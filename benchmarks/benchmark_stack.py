from aws_cdk import (
    Duration,
    RemovalPolicy,
    Stack,
)
from aws_cdk import aws_cloudwatch as cloudwatch
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_kms as kms
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_stepfunctions as sfn
from aws_cdk import aws_stepfunctions_tasks as tasks
from aws_cdk.aws_lambda_python_alpha import PythonFunction
from constructs import Construct

# Handler paths
PYDYNOX_HANDLER = "src/pydynox"
BOTO3_HANDLER = "src/boto3"
PYNAMODB_HANDLER = "src/pynamodb"


class BenchmarkStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # DynamoDB table
        table = dynamodb.Table(
            self,
            "BenchmarkTable",
            table_name="pydynox-benchmark",
            partition_key=dynamodb.Attribute(name="pk", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="sk", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # S3 bucket
        bucket = s3.Bucket(
            self,
            "BenchmarkBucket",
            bucket_name=f"pydynox-benchmark-{self.account}-{self.region}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # KMS key
        kms_key = kms.Key(
            self,
            "BenchmarkKey",
            description="KMS key for pydynox encryption benchmarks",
            removal_policy=RemovalPolicy.DESTROY,
        )

        # ============================================================
        # PYDYNOX LAMBDAS - ARM64
        # ============================================================
        pydynox_128_arm = self._create_lambda(
            "Pydynox128Arm",
            PYDYNOX_HANDLER,
            128,
            lambda_.Architecture.ARM_64,
            "arm64",
            table,
            bucket,
            kms_key,
        )
        pydynox_256_arm = self._create_lambda(
            "Pydynox256Arm",
            PYDYNOX_HANDLER,
            256,
            lambda_.Architecture.ARM_64,
            "arm64",
            table,
            bucket,
            kms_key,
        )
        pydynox_512_arm = self._create_lambda(
            "Pydynox512Arm",
            PYDYNOX_HANDLER,
            512,
            lambda_.Architecture.ARM_64,
            "arm64",
            table,
            bucket,
            kms_key,
        )
        pydynox_1024_arm = self._create_lambda(
            "Pydynox1024Arm",
            PYDYNOX_HANDLER,
            1024,
            lambda_.Architecture.ARM_64,
            "arm64",
            table,
            bucket,
            kms_key,
        )
        pydynox_2048_arm = self._create_lambda(
            "Pydynox2048Arm",
            PYDYNOX_HANDLER,
            2048,
            lambda_.Architecture.ARM_64,
            "arm64",
            table,
            bucket,
            kms_key,
        )

        # ============================================================
        # PYDYNOX LAMBDAS - X86_64
        # ============================================================
        pydynox_128_x86 = self._create_lambda(
            "Pydynox128X86",
            PYDYNOX_HANDLER,
            128,
            lambda_.Architecture.X86_64,
            "x86_64",
            table,
            bucket,
            kms_key,
        )
        pydynox_256_x86 = self._create_lambda(
            "Pydynox256X86",
            PYDYNOX_HANDLER,
            256,
            lambda_.Architecture.X86_64,
            "x86_64",
            table,
            bucket,
            kms_key,
        )
        pydynox_512_x86 = self._create_lambda(
            "Pydynox512X86",
            PYDYNOX_HANDLER,
            512,
            lambda_.Architecture.X86_64,
            "x86_64",
            table,
            bucket,
            kms_key,
        )
        pydynox_1024_x86 = self._create_lambda(
            "Pydynox1024X86",
            PYDYNOX_HANDLER,
            1024,
            lambda_.Architecture.X86_64,
            "x86_64",
            table,
            bucket,
            kms_key,
        )
        pydynox_2048_x86 = self._create_lambda(
            "Pydynox2048X86",
            PYDYNOX_HANDLER,
            2048,
            lambda_.Architecture.X86_64,
            "x86_64",
            table,
            bucket,
            kms_key,
        )

        # ============================================================
        # BOTO3 LAMBDAS - ARM64
        # ============================================================
        boto3_128_arm = self._create_lambda(
            "Boto3128Arm",
            BOTO3_HANDLER,
            128,
            lambda_.Architecture.ARM_64,
            "arm64",
            table,
            bucket,
            kms_key,
        )
        boto3_256_arm = self._create_lambda(
            "Boto3256Arm",
            BOTO3_HANDLER,
            256,
            lambda_.Architecture.ARM_64,
            "arm64",
            table,
            bucket,
            kms_key,
        )
        boto3_512_arm = self._create_lambda(
            "Boto3512Arm",
            BOTO3_HANDLER,
            512,
            lambda_.Architecture.ARM_64,
            "arm64",
            table,
            bucket,
            kms_key,
        )
        boto3_1024_arm = self._create_lambda(
            "Boto3_1024Arm",
            BOTO3_HANDLER,
            1024,
            lambda_.Architecture.ARM_64,
            "arm64",
            table,
            bucket,
            kms_key,
        )
        boto3_2048_arm = self._create_lambda(
            "Boto32048Arm",
            BOTO3_HANDLER,
            2048,
            lambda_.Architecture.ARM_64,
            "arm64",
            table,
            bucket,
            kms_key,
        )

        # ============================================================
        # BOTO3 LAMBDAS - X86_64
        # ============================================================
        boto3_128_x86 = self._create_lambda(
            "Boto3128X86",
            BOTO3_HANDLER,
            128,
            lambda_.Architecture.X86_64,
            "x86_64",
            table,
            bucket,
            kms_key,
        )
        boto3_256_x86 = self._create_lambda(
            "Boto3256X86",
            BOTO3_HANDLER,
            256,
            lambda_.Architecture.X86_64,
            "x86_64",
            table,
            bucket,
            kms_key,
        )
        boto3_512_x86 = self._create_lambda(
            "Boto3512X86",
            BOTO3_HANDLER,
            512,
            lambda_.Architecture.X86_64,
            "x86_64",
            table,
            bucket,
            kms_key,
        )
        boto3_1024_x86 = self._create_lambda(
            "Boto31024X86",
            BOTO3_HANDLER,
            1024,
            lambda_.Architecture.X86_64,
            "x86_64",
            table,
            bucket,
            kms_key,
        )
        boto3_2048_x86 = self._create_lambda(
            "Boto32048X86",
            BOTO3_HANDLER,
            2048,
            lambda_.Architecture.X86_64,
            "x86_64",
            table,
            bucket,
            kms_key,
        )

        # ============================================================
        # PYNAMODB LAMBDAS - ARM64
        # ============================================================
        pynamodb_128_arm = self._create_lambda(
            "Pynamodb128Arm",
            PYNAMODB_HANDLER,
            128,
            lambda_.Architecture.ARM_64,
            "arm64",
            table,
            bucket,
            kms_key,
        )
        pynamodb_256_arm = self._create_lambda(
            "Pynamodb256Arm",
            PYNAMODB_HANDLER,
            256,
            lambda_.Architecture.ARM_64,
            "arm64",
            table,
            bucket,
            kms_key,
        )
        pynamodb_512_arm = self._create_lambda(
            "Pynamodb512Arm",
            PYNAMODB_HANDLER,
            512,
            lambda_.Architecture.ARM_64,
            "arm64",
            table,
            bucket,
            kms_key,
        )
        pynamodb_1024_arm = self._create_lambda(
            "Pynamodb1024Arm",
            PYNAMODB_HANDLER,
            1024,
            lambda_.Architecture.ARM_64,
            "arm64",
            table,
            bucket,
            kms_key,
        )
        pynamodb_2048_arm = self._create_lambda(
            "Pynamodb2048Arm",
            PYNAMODB_HANDLER,
            2048,
            lambda_.Architecture.ARM_64,
            "arm64",
            table,
            bucket,
            kms_key,
        )

        # ============================================================
        # PYNAMODB LAMBDAS - X86_64
        # ============================================================
        pynamodb_128_x86 = self._create_lambda(
            "Pynamodb128X86",
            PYNAMODB_HANDLER,
            128,
            lambda_.Architecture.X86_64,
            "x86_64",
            table,
            bucket,
            kms_key,
        )
        pynamodb_256_x86 = self._create_lambda(
            "Pynamodb256X86",
            PYNAMODB_HANDLER,
            256,
            lambda_.Architecture.X86_64,
            "x86_64",
            table,
            bucket,
            kms_key,
        )
        pynamodb_512_x86 = self._create_lambda(
            "Pynamodb512X86",
            PYNAMODB_HANDLER,
            512,
            lambda_.Architecture.X86_64,
            "x86_64",
            table,
            bucket,
            kms_key,
        )
        pynamodb_1024_x86 = self._create_lambda(
            "Pynamodb1024X86",
            PYNAMODB_HANDLER,
            1024,
            lambda_.Architecture.X86_64,
            "x86_64",
            table,
            bucket,
            kms_key,
        )
        pynamodb_2048_x86 = self._create_lambda(
            "Pynamodb2048X86",
            PYNAMODB_HANDLER,
            2048,
            lambda_.Architecture.X86_64,
            "x86_64",
            table,
            bucket,
            kms_key,
        )

        # ============================================================
        # STEP FUNCTIONS
        # ============================================================
        pydynox_parallel = sfn.Parallel(self, "RunPydynox", result_path=sfn.JsonPath.DISCARD)
        for fn in [
            pydynox_128_arm,
            pydynox_256_arm,
            pydynox_512_arm,
            pydynox_1024_arm,
            pydynox_2048_arm,
            pydynox_128_x86,
            pydynox_256_x86,
            pydynox_512_x86,
            pydynox_1024_x86,
            pydynox_2048_x86,
        ]:
            pydynox_parallel.branch(
                tasks.LambdaInvoke(
                    self, f"Task{fn.node.id}", lambda_function=fn, result_path=sfn.JsonPath.DISCARD
                )
            )

        boto3_parallel = sfn.Parallel(self, "RunBoto3", result_path=sfn.JsonPath.DISCARD)
        for fn in [
            boto3_128_arm,
            boto3_256_arm,
            boto3_512_arm,
            boto3_1024_arm,
            boto3_2048_arm,
            boto3_128_x86,
            boto3_256_x86,
            boto3_512_x86,
            boto3_1024_x86,
            boto3_2048_x86,
        ]:
            boto3_parallel.branch(
                tasks.LambdaInvoke(
                    self, f"Task{fn.node.id}", lambda_function=fn, result_path=sfn.JsonPath.DISCARD
                )
            )

        pynamodb_parallel = sfn.Parallel(self, "RunPynamodb", result_path=sfn.JsonPath.DISCARD)
        for fn in [
            pynamodb_128_arm,
            pynamodb_256_arm,
            pynamodb_512_arm,
            pynamodb_1024_arm,
            pynamodb_2048_arm,
            pynamodb_128_x86,
            pynamodb_256_x86,
            pynamodb_512_x86,
            pynamodb_1024_x86,
            pynamodb_2048_x86,
        ]:
            pynamodb_parallel.branch(
                tasks.LambdaInvoke(
                    self, f"Task{fn.node.id}", lambda_function=fn, result_path=sfn.JsonPath.DISCARD
                )
            )

        definition = pydynox_parallel.next(boto3_parallel).next(pynamodb_parallel)

        state_machine = sfn.StateMachine(
            self,
            "BenchmarkStateMachine",
            state_machine_name="pydynox-benchmark",
            definition_body=sfn.DefinitionBody.from_chainable(definition),
            timeout=Duration.minutes(30),
        )

        # EventBridge - every minute
        events.Rule(
            self,
            "HourlyRule",
            schedule=events.Schedule.rate(Duration.minutes(1)),
            targets=[targets.SfnStateMachine(state_machine)],
        )

        # Dashboard
        self._create_dashboard()

    def _create_lambda(
        self,
        name: str,
        entry: str,
        memory: int,
        arch: lambda_.Architecture,
        arch_env: str,
        table: dynamodb.Table,
        bucket: s3.Bucket,
        kms_key: kms.Key,
    ) -> PythonFunction:
        fn = PythonFunction(
            self,
            name,
            runtime=lambda_.Runtime.PYTHON_3_12,
            entry=entry,
            index="handler.py",
            handler="handler",
            memory_size=memory,
            architecture=arch,
            timeout=Duration.minutes(5),
            environment={
                "TABLE_NAME": table.table_name,
                "BUCKET_NAME": bucket.bucket_name,
                "KMS_KEY_ID": kms_key.key_id,
                "MEMORY_SIZE": str(memory),
                "ARCHITECTURE": arch_env,
                "POWERTOOLS_SERVICE_NAME": "pydynox-benchmark",
                "POWERTOOLS_METRICS_NAMESPACE": "pydynox/benchmarks",
            },
        )
        table.grant_read_write_data(fn)
        bucket.grant_read_write(fn)
        kms_key.grant_encrypt_decrypt(fn)
        return fn

    def _create_dashboard(self) -> cloudwatch.Dashboard:
        dashboard = cloudwatch.Dashboard(
            self,
            "Dashboard",
            dashboard_name="pydynox-benchmark",
            variables=[
                cloudwatch.DashboardVariable(
                    id="memory",
                    type=cloudwatch.VariableType.PROPERTY,
                    label="Memory",
                    input_type=cloudwatch.VariableInputType.SELECT,
                    value="Memory",
                    values=cloudwatch.Values.from_values(
                        cloudwatch.VariableValue(value="128"),
                        cloudwatch.VariableValue(value="256"),
                        cloudwatch.VariableValue(value="512"),
                        cloudwatch.VariableValue(value="1024"),
                        cloudwatch.VariableValue(value="2048"),
                    ),
                    default_value=cloudwatch.DefaultValue.value("1024"),
                    visible=True,
                ),
                cloudwatch.DashboardVariable(
                    id="arch",
                    type=cloudwatch.VariableType.PROPERTY,
                    label="Architecture",
                    input_type=cloudwatch.VariableInputType.SELECT,
                    value="Architecture",
                    values=cloudwatch.Values.from_values(
                        cloudwatch.VariableValue(value="arm64"),
                        cloudwatch.VariableValue(value="x86_64"),
                    ),
                    default_value=cloudwatch.DefaultValue.value("x86_64"),
                    visible=True,
                ),
            ],
        )
        namespace = "pydynox/benchmarks"
        service = "pydynox-benchmark"

        def metric(op: str, lib: str, stat: str = "p50"):
            return cloudwatch.Metric(
                namespace=namespace,
                metric_name=op,
                dimensions_map={
                    "Architecture": "${arch}",
                    "Library": lib,
                    "Memory": "${memory}",
                    "service": service,
                },
                statistic=stat,
                label=lib,
            )

        # Header
        dashboard.add_widgets(
            cloudwatch.TextWidget(markdown="# pydynox Benchmarks", width=24, height=1)
        )

        # Basic ops
        dashboard.add_widgets(
            cloudwatch.TextWidget(markdown="## Basic Operations", width=24, height=1)
        )
        for op in ["put_item", "get_item", "update_item", "delete_item", "query"]:
            dashboard.add_widgets(
                cloudwatch.GraphWidget(
                    title=f"{op} p50",
                    width=12,
                    height=6,
                    left=[metric(op, "pydynox"), metric(op, "boto3"), metric(op, "pynamodb")],
                ),
                cloudwatch.GraphWidget(
                    title=f"{op} p99",
                    width=12,
                    height=6,
                    left=[
                        metric(op, "pydynox", "p99"),
                        metric(op, "boto3", "p99"),
                        metric(op, "pynamodb", "p99"),
                    ],
                ),
            )

        # Batch ops
        dashboard.add_widgets(
            cloudwatch.TextWidget(markdown="## Batch Operations", width=24, height=1)
        )
        for op in ["batch_write", "batch_get"]:
            dashboard.add_widgets(
                cloudwatch.GraphWidget(
                    title=op,
                    width=12,
                    height=6,
                    left=[metric(op, "pydynox"), metric(op, "boto3"), metric(op, "pynamodb")],
                ),
            )

        # Advanced ops
        dashboard.add_widgets(
            cloudwatch.TextWidget(markdown="## Advanced Operations", width=24, height=1)
        )
        for put_op, get_op in [
            ("put_encrypted", "get_encrypted"),
            ("put_compressed", "get_compressed"),
            ("put_s3", "get_s3"),
        ]:
            dashboard.add_widgets(
                cloudwatch.GraphWidget(
                    title=put_op,
                    width=12,
                    height=6,
                    left=[
                        metric(put_op, "pydynox"),
                        metric(put_op, "boto3"),
                        metric(put_op, "pynamodb"),
                    ],
                ),
                cloudwatch.GraphWidget(
                    title=get_op,
                    width=12,
                    height=6,
                    left=[
                        metric(get_op, "pydynox"),
                        metric(get_op, "boto3"),
                        metric(get_op, "pynamodb"),
                    ],
                ),
            )

        return dashboard
