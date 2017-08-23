#!/bin/bash
set -euo pipefail

# Make directory for project
mkdir -p /home/datamade/semabot

cd /opt/codedeploy-agent/deployment-root/$DEPLOYMENT_GROUP_ID/$DEPLOYMENT_ID/deployment-archive/ && chown -R datamade.datamade . && sudo -H -u datamade blackbox_postdeploy
