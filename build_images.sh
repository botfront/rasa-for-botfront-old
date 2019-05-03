#!/usr/bin/env bash
docker build -f Dockerfile_nlu -t botfront/rasa-nlu-bf:latest .
docker build -f Dockerfile_core -t botfront/rasa-core-bf:latest .