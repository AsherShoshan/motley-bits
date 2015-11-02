"""
SplitReviews:
   This script takes 2 files:
   1. commiters file which contains a list of names that can commit code.
       alice
       #bob
       carl
   2. reviwers file which contains a list of names that should review this code

   Usage:
   python split_reviewers.py -c <committers_file> -r <reviewers_file>

"""
#!/usr/bin/python

import random
import sys
import argparse
import smtplib

from datetime import datetime
from email.mime.text import MIMEText
from ConfigParser import ConfigParser


class Person(object):

    def __init__(self, name, group):
        self._name = name
        self._group = group

    def __str__(self):
        return str(self.name)

    def __eq__(self, other):
        return self.name == other.name and self.group == other.group

    def __repr__(self):
        return str(self._name)

    @property
    def name(self):
        return self._name

    @property
    def group(self):
        return self._group


class SplitReviews(object):

    commiters = []
    reviewers = {}
    who_can_review_each_commit = {}
    gerrit_url = None
    results = ''

    def __init__(self, committers_file, reviewers_file, gerrit_url=None):
        self._init_committers_list(committers_file)
        self._init_reviewers_dict(reviewers_file)
        self._init_who_can_review_dict()
        self.gerrit_url = gerrit_url

    def _init_committers_list(self, committers_file):
        self.committers = self._file_to_list(committers_file)

    def _init_reviewers_dict(self, reviewers_file):
        reviewers_list = self._file_to_list(reviewers_file)
        self.reviewers = {reviewer: [] for reviewer in reviewers_list}

    def _init_who_can_review_dict(self):
        self.who_can_review_each_commit = {
            committer: self.who_can_review_committer(committer)
            for committer in self.committers
            }

    def who_can_review_committer(self, committer):
        possible_reviewers = []
        for reviewer in self.reviewers.keys():
            if (
                    reviewer.group != committer.group
                    and committer not in self.reviewers[reviewer]
            ):
                possible_reviewers.append(reviewer)
        return possible_reviewers

    def _file_to_list(self, file_name):
        dummy_list = []
        with open(file_name, 'r') as fd:
            for line in fd:
                if not line.startswith('#') and line:
                    dummy_list.append(self.create_person(line))
        random.shuffle(dummy_list)
        return dummy_list

    def create_person(self, line):
        name, group = line.replace('\n', '').replace(' ', '').split(',')
        return Person(name, group)

    def print_reviewer_and_reviewee(self):
        for reviewer, reviewees in self.reviewers.items():
            if not (self.reviewers[reviewer]):
                continue
            review_list = '%s to review %s' % (reviewer, reviewees)
            owners = '(owner:%s' % (self.reviewers[reviewer].pop())
            while self.reviewers[reviewer]:
                owners += '+OR+owner:%s' % self.reviewers[reviewer].pop()

            self.results += review_list + '\n'

            if self.gerrit_url:
                status = ')+AND+status:open'
                gerrit_query = "{0}/{1}{2}".format(
                    self.gerrit_url, owners, status
                )
                self.results += gerrit_query + '\n\n'

        print self.results

    def email_results(self, mail_server, from_email, to_email=[]):

        print 'Sending email to %s' % to_email
        s = smtplib.SMTP(mail_server)

        msg = MIMEText(self.results)

        msg['Subject'] = 'Reviews for %s\%s' % (
            datetime.now().month, datetime.now().year
        )
        msg['From'] = from_email
        msg['To'] = from_email
        s.sendmail(from_email, to_email, msg.as_string())
        s.quit()

    def split_evenly_or_almost_evenly(self):
        random.shuffle(self.committers)
        div = len(self.committers)/float(len(self.reviewers))
        return [self.committers[int(round(div * i)): int(round(div * (i + 1)))]
                for i in xrange(len(self.reviewers))]

    def who_review_whom(self):
        ppl_to_be_reviewed = self.split_evenly_or_almost_evenly()
        the_reviewers = self.reviewers.keys()
        random.shuffle(the_reviewers)
        for reviewer in the_reviewers:
            random.shuffle(ppl_to_be_reviewed)
            group_to_review = random.choice(ppl_to_be_reviewed)
            self.reviewers[reviewer] = group_to_review
            ppl_to_be_reviewed.remove(group_to_review)

    def divide_reviews(self, min_reviews):
        for i in xrange(min_reviews):
            for committer in self.committers:
                reviewer = self.choose_reviewer(committer)
                if reviewer:
                    self.reviewers[reviewer].append(committer)

    def choose_reviewer(self, committer):
        chosen_reviewer = None
        chosen_len = 0
        for reviewer in self.who_can_review_each_commit[committer]:
            reviewer_len = len(self.reviewers[reviewer])
            if chosen_reviewer is None:
                chosen_reviewer = reviewer
                chosen_len = reviewer_len
            elif reviewer_len < chosen_len:
                chosen_reviewer = reviewer
                chosen_len = reviewer_len
        self.remove_possible_reviewer(committer, chosen_reviewer)
        return chosen_reviewer

    def remove_possible_reviewer(self, committer, reviewer):
        if reviewer is None:
            print("ERROR: couldn't find more reviewers for %s" % committer)
        else:
            self.who_can_review_each_commit[committer].remove(reviewer)


def main(argv):

    parser = argparse.ArgumentParser(
        description='Split gerrit reviews among reviewers'
    )

    parser.add_argument(
        '--committers',
        action='store',
        dest='committers',
        help='File contains committers: committer, team'
    )

    parser.add_argument(
        '--reviewers',
        action='store',
        dest='reviewers',
        help='File contains reviewers: reviewer, team'
    )

    parser.add_argument(
        '--reviews-per-commit',
        action='store',
        dest='min_reviews_per_commit',
        help='Number of reviewers per commit', type=int
    )

    parser.add_argument(
        '--with-gerrit-url',
        action='store_true',
        default=False,
        help='Print Gerrit URL defined in .splitreview.ini'
    )

    parser.add_argument(
        '--send-email',
        action='store_true',
        default=False,
        help='Send email (defined in .splitreview.ini)'
    )

    config = ConfigParser()

    config.read('.splitreviews.ini')

    args = parser.parse_args()

    if args.with_gerrit_url:
        x = SplitReviews(
            args.committers,
            args.reviewers,
            gerrit_url=config.get('parameters', 'gerrit_url')
        )
    else:
        x = SplitReviews(args.committers, args.reviewers)

    if args.min_reviews_per_commit:
        x.divide_reviews(args.min_reviews_per_commit)
    else:
        x.who_review_whom()

    x.print_reviewer_and_reviewee()

    if args.send_email:
        x.email_results(
            config.get('parameters', 'mail_server'),
            config.get('parameters', 'from_email'),
            config.get('parameters', 'to_email')
        )


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(sys.argv[1:])
    else:
        print 'Try %s -h' % sys.argv[0]
