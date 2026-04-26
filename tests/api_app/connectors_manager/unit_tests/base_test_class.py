# This file is a part of IntelOwl https://github.com/intelowlproject/IntelOwl
# See the file 'LICENSE' for copying permission.

from contextlib import ExitStack

from django.contrib.auth import get_user_model
from django.test import TestCase

from api_app.analyzables_manager.models import Analyzable
from api_app.choices import Classification
from api_app.connectors_manager.models import ConnectorConfig, ConnectorReport
from api_app.models import Job, Parameter, PluginConfig


class BaseConnectorTest(TestCase):
    connector_class = None
    fixtures = ["api_app/fixtures/0001_user.json"]

    def setUp(self):
        super().setUp()
        User = get_user_model()
        self.superuser = User.objects.get(is_superuser=True)

    def _setup_connector(
        self,
        connector_class_name,
        observable_name="8.8.8.8",
        observable_type=Classification.IP,
        params=None,
    ):
        """
        Setup a connector with required side-effects (Job, Analyzable, etc.)
        Returns (connector, job, config, analyzable) so callers can clean up
        using a direct reference to the created Analyzable instance.
        """
        config = ConnectorConfig.objects.get(python_module__module__endswith=f".{connector_class_name}")

        # Use update_or_create so repeated calls with different param values
        # always reflect the intended configuration rather than leaving stale rows.
        if params:
            for name, value in params.items():
                param = Parameter.objects.get(python_module=config.python_module, name=name)
                PluginConfig.objects.update_or_create(
                    parameter=param,
                    connector_config=config,
                    defaults={"value": value, "for_organization": False, "owner": None},
                )

        # Keep a direct reference so the finally block can delete the exact row
        # rather than re-querying by name (which is not unique).
        analyzable = Analyzable.objects.create(name=observable_name, classification=observable_type)
        job = Job.objects.create(
            analyzable=analyzable,
            user=self.superuser,
            status=Job.STATUSES.REPORTED_WITHOUT_FAILS.value,
        )
        job.connectors_to_execute.set([config])

        connector = self.connector_class(config)
        connector.job_id = job.pk

        return connector, job, config, analyzable

    def get_mocked_response(self):
        """
        Subclasses should override this to provide patch context manager(s).

        Supported return values are:
        - a single patch/context manager
        - a list or tuple of patches/context managers
        - an empty value when no patching is needed
        """
        return []

    def _apply_patches(self, patches):
        if not patches:
            return ExitStack()

        stack = ExitStack()
        if isinstance(patches, (list, tuple)):
            for p in patches:
                stack.enter_context(p)
        else:
            stack.enter_context(patches)
        return stack

    def execute_run_logic(
        self,
        connector_class_name,
        observable_name="8.8.8.8",
        observable_type=Classification.IP,
        params=None,
    ):
        """
        Generic test runner for connectors.
        Exceptions are allowed to propagate so that the full traceback is
        visible in the test output and assertion failures are not swallowed.
        """
        if not self.connector_class:
            self.skipTest("connector_class not set")

        connector, job, config, analyzable = self._setup_connector(
            connector_class_name, observable_name, observable_type, params
        )

        patches = self.get_mocked_response()
        try:
            with self._apply_patches(patches):
                from kombu import uuid

                connector.report = config.generate_empty_report(
                    job, str(uuid()), ConnectorReport.STATUSES.RUNNING.value
                )
                connector.config(params or {})
                connector.before_run()
                response = connector.run()

                self.assertIsInstance(response, (dict, list))
                return response
        finally:
            # Delete using the direct reference captured at creation time to
            # avoid accidentally removing an unrelated Analyzable that shares
            # the same name.
            job.delete()
            analyzable.delete()
