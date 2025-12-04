#!/bin/bash
set -e

source /etc/profile.d/cloud-environment.sh

if [[ ${ENVGROUP} == "nonprod" ]]; then
  nex_url="nexus.itt.aws.odev.com.au"
  dockerhub_url="dockerhub.itt.aws.odev.com.au"
else
  nex_url="nexus.itt.aws.oprd.com.au"
  dockerhub_url="dockerhub.itt.aws.oprd.com.au"
fi
docker build --build-arg NEXUS_URL=${nex_url} \
             --build-arg DOCKER_HUB_URL=${dockerhub_url} \
             -t builder .

docker kill builder || true
docker rm builder || true

docker run -v /etc/profile.d/cloud-environment.sh:/etc/profile.d/cloud-environment.sh \
           -p 8000:8000 -d \
           --name builder builder:latest

builder_ip=$(docker inspect builder | jq -r '.[0].NetworkSettings.IPAddress')

# Wait for builder to fully start
sleep 10

curl -X POST "http://${builder_ip}:8000/build/" \
     -H "Content-Type: application/json" \
     -d '{"component": "ecs-jenkins"}'

docker kill builder || true
docker rm builder || true
