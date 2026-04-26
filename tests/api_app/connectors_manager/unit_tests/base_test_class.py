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
        """
        config = ConnectorConfig.objects.get(
            python_module__module__endswith=f".{connector_class_name}"
        )

        # Create required PluginConfigs if params are provided
        if params:
            for name, value in params.items():
                param = Parameter.objects.get(
                    python_module=config.python_module, name=name
                )
                PluginConfig.objects.get_or_create(
                    parameter=param,
                    connector_config=config,
                    defaults={"value": value, "for_organization": False, "owner": None},
                )

        analyzable = Analyzable.objects.create(
            name=observable_name, classification=observable_type
        )
        job = Job.objects.create(
            analyzable=analyzable,
            user=self.superuser,
            status=Job.STATUSES.REPORTED_WITHOUT_FAILS.value,
        )
        job.connectors_to_execute.set([config])

        connector = self.connector_class(config)
        connector.job_id = job.pk

        return connector, job, config

    def get_mocked_response(self):
        """
        Subclasses should override this to provide a list of patches.
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
        """
        if not self.connector_class:
            self.skipTest("connector_class not set")

        connector, job, config = self._setup_connector(
            connector_class_name, observable_name, observable_type, params
        )

        patches = self.get_mocked_response()
        with self._apply_patches(patches):
            try:
                from kombu import uuid

                connector.report = config.generate_empty_report(
                    job, str(uuid()), ConnectorReport.STATUSES.RUNNING.value
                )
                connector.config(params or {})
                connector.before_run()
                response = connector.run()

                self.assertIsInstance(response, (dict, list))

                return response
            except Exception as e:
                self.fail(f"Connector {self.connector_class.__name__} failed: {e}")
            finally:
                job.delete()
                analyzable = Analyzable.objects.filter(name=observable_name).first()
                if analyzable:
                    analyzable.delete()
