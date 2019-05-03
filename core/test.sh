#!/usr/bin/env bash
python -m rasa_addons.tests -d  domains/aggregated_domains.yaml -m models/dialogue/ -t test_cases/ -r rules.yml --distinct