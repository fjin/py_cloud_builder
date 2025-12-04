#!/bin/bash
set -e

echo "Set Default region ..."
export AWS_DEFAULT_REGION=ap-southeast-2

echo "Deleting CloudFormation Stack: ecs-jenkins-instance-profile-stack"
aws cloudformation delete-stack --stack-name ecs-jenkins-instance-profile-stack

echo "Waiting for stack deletion to complete..."
aws cloudformation wait stack-delete-complete --stack-name ecs-jenkins-instance-profile-stack

echo "Stack ecs-jenkins-instance-profile-stack has been successfully deleted."