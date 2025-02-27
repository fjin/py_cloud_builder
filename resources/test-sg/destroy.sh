#!/bin/bash
set -e

echo "Set Default region ..."
export AWS_DEFAULT_REGION=ap-southeast-2

echo "Deleting CloudFormation Stack: test-sg-stack"
aws cloudformation delete-stack --stack-name test-sg-stack

echo "Waiting for stack deletion to complete..."
aws cloudformation wait stack-delete-complete --stack-name test-sg-stack

echo "Stack test-sg-stack has been successfully deleted."