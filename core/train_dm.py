import argparse
import glob
import os
import time
import logging

from rasa_addons.domains_merger import DomainsMerger
from rasa_addons.superagent import SuperAgent
from rasa_core.policies.memoization import MemoizationPolicy, AugmentedMemoizationPolicy
from rasa_core.policies.keras_policy import KerasPolicy
from rasa_core.agent import Agent


logger = logging.getLogger()


def concatenate_storyfiles(folder_path, prefix='stories', output='aggregated_stories.md'):
    path_pattern = u'{}/{}*.md'.format(folder_path, prefix)
    filenames = glob.glob(path_pattern)
    with open(output, 'w') as outfile:
        for fname in filenames:
            with open(fname, 'r') as infile:
                for line in infile:
                    outfile.write(line)
                outfile.write("\n")


def train(stories_path, domain_path, policy_path):
    root = os.path.dirname(__file__)
    domain_path = os.path.join(root, domain_path)
    stories_path = os.path.join(root, stories_path)
    # generate_questions_data(stories_path, domain_path)
    concatenate_storyfiles(stories_path, 'stories', os.path.join(stories_path, 'aggregated_stories.md'))
    training_data_file = os.path.join(stories_path, 'aggregated_stories.md')

    DomainsMerger(domain_path).merge().dump()
    domain_path = os.path.join(domain_path, 'aggregated_domains.yaml')

    from rasa_core.featurizers import (MaxHistoryTrackerFeaturizer,
                                       BinarySingleStateFeaturizer)

    policies = [
        MemoizationPolicy( max_history=3),
        KerasPolicy(MaxHistoryTrackerFeaturizer(BinarySingleStateFeaturizer(), max_history=3))
    ]
    agent = SuperAgent(domain_path, policies=policies)
    training_data = agent.load_data(training_data_file)

    agent.train(training_data, epochs=200, validation_split=0.0)
    agent.persist(policy_path)
    logging.basicConfig(level="WARN")


def create_argparser():
    parser = argparse.ArgumentParser(
        description='Trains the bot.')

    parser.add_argument('-s', '--stories', help="Stories path")
    parser.add_argument('-d', '--domain', help="Domain path")
    parser.add_argument('-p', '--policy', help="Policy path")
    return parser


if __name__ == "__main__":
    debug_mode = True
    parser = create_argparser()
    args = parser.parse_args()
    start_time = time.time()
    train(args.stories, args.domain, args.policy)
    print("--- %s seconds ---" % (time.time() - start_time))
