#!/usr/bin/env python3
import aws_cdk as cdk
from benchmark_stack import BenchmarkStack

app = cdk.App()
BenchmarkStack(app, "PydynoxBenchmarkStack")
app.synth()
