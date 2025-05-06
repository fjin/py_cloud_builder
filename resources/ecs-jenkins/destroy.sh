#!/bin/bash
set -e

echo "Set Default region ..."
export AWS_DEFAULT_REGION=ap-southeast-2

echo "Deleting CloudFormation Stack: ecs-jenkins-stack"
aws cloudformation delete-stack --stack-name ecs-jenkins-stack

echo "Waiting for stack deletion to complete..."
aws cloudformation wait stack-delete-complete --stack-name ecs-jenkins-stack

echo "Stack ecs-jenkins-stack has been successfully deleted."