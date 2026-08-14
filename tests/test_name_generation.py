#!/usr/bin/env python

"""Test tvnamer's EpisodeInfo file name generation
"""

import os
import datetime
from typing import Any

from helpers import assertEquals

from tvnamer.data import (EpisodeInfo, DatedEpisodeInfo, NoSeasonEpisodeInfo)
from test_files import files

from tvnamer.tvdb_v4 import Series


class FixtureTvdb(object):
    """Deterministic v4-shaped data generated from the test expectations."""
    def __init__(self, test):
        self.test = test

    def search(self, _name):
        episodes = []
        for number, name in zip(self.test['episodenumbers'], self.test['episodenames']):
            if isinstance(number, datetime.date):
                episodes.append({'aired': str(number), 'name': name, 'seasonNumber': 1})
            else:
                episodes.append({
                    'number': number,
                    'seasonNumber': self.test.get('seasonnumber') or 1,
                    'name': name,
                    'absoluteNumber': number,
                })
        return Series(1, self.test['correctedseriesname'], episodes)


def verify_name_gen(curtest):
    # type: (Any) -> None
    if "seasonnumber" in curtest:
        ep = EpisodeInfo(
            seriesname = curtest['parsedseriesname'],
            seasonnumber = curtest['seasonnumber'],
            episodenumbers = curtest['episodenumbers'])
    elif any([isinstance(x, datetime.date) for x in curtest['episodenumbers']]):
        ep = DatedEpisodeInfo(
            seriesname = curtest['parsedseriesname'],
            episodenumbers = curtest['episodenumbers'])
    else:
        ep = NoSeasonEpisodeInfo(
            seriesname = curtest['parsedseriesname'],
            episodenumbers = curtest['episodenumbers'])

    ep.populate_from_tvdb(FixtureTvdb(curtest), force_name=curtest.get("force_name"))

    assert ep.seriesname is not None, "Corrected series name was none"
    assert ep.episodename is not None, "Episode name was None"

    assertEquals(ep.seriesname, curtest['correctedseriesname'])
    assertEquals(ep.episodename, curtest['episodenames'])


def test_name_generation_on_testfiles():
    # type: () -> None

    for category, testcases in files.items():
        for curtest in testcases:
            verify_name_gen(curtest)


def test_single_episode():
    # type: () -> None
    """Simple episode name, with show/season/episode/name/filename
    """

    ep = EpisodeInfo(
        seriesname = 'Scrubs',
        seasonnumber = 1,
        episodenumbers = [2],
        episodename = ['My Mentor'],
        filename = 'scrubs.example.file.avi')

    assertEquals(
        ep.generate_filename(),
        'Scrubs - [01x02] - My Mentor.avi')


def test_multi_episodes_continuous():
    # type: () -> None
    """A two-part episode should not have the episode name repeated
    """
    ep = EpisodeInfo(
        seriesname = 'Stargate SG-1',
        seasonnumber = 1,
        episodenumbers = [1, 2],
        episodename = [
            'Children of the Gods (1)',
            'Children of the Gods (2)'],
        filename = 'stargate.example.file.avi')

    assertEquals(
        ep.generate_filename(),
        'Stargate SG-1 - [01x01-02] - Children of the Gods (1-2).avi')


def test_episode_numeric_title():
    # type: () -> None
    """An episode with a name starting with a number should not be
    detected as a range
    """

    ep = EpisodeInfo(
        seriesname = 'Star Trek TNG',
        seasonnumber = 1,
        episodenumbers = [15],
        episodename = [
            '11001001'
        ],
        filename = 'STTNG-S01E15-11001001.avi')

    assertEquals(
        ep.generate_filename(),
        'Star Trek TNG - [01x15] - 11001001.avi')


def test_multi_episodes_seperate():
    # type: () -> None
    """File with two episodes, but with different names
    """
    ep = EpisodeInfo(
        seriesname = 'Stargate SG-1',
        seasonnumber = 1,
        episodenumbers = [2, 3],
        episodename = [
            'Children of the Gods (2)',
            'The Enemy Within'],
        filename = 'stargate.example.file.avi')

    assertEquals(
        ep.generate_filename(),
        'Stargate SG-1 - [01x02-03] - Children of the Gods (2), The Enemy Within.avi')


def test_simple_no_ext():
    # type: () -> None
    """Simple episode with out extension
    """
    ep = EpisodeInfo(
        seriesname = 'Scrubs',
        seasonnumber = 1,
        episodenumbers = [2],
        episodename = ['My Mentor'],
        filename = None)

    assertEquals(
        ep.generate_filename(),
        'Scrubs - [01x02] - My Mentor')


def test_no_name():
    # type: () -> None
    """Episode without a name
    """
    ep = EpisodeInfo(
        seriesname = 'Scrubs',
        seasonnumber = 1,
        episodenumbers = [2],
        episodename = None,
        filename = 'scrubs.example.file.avi')

    assertEquals(
        ep.generate_filename(),
        'Scrubs - [01x02].avi')


def test_episode_no_name_no_ext():
    # type: () -> None
    """EpisodeInfo with no name or extension
    """
    ep = EpisodeInfo(
        seriesname = 'Scrubs',
        seasonnumber = 1,
        episodenumbers = [2],
        episodename = None,
        filename = None)

    assertEquals(
        ep.generate_filename(),
        'Scrubs - [01x02]')


def test_noseason_no_name_no_ext():
    # type: () -> None
    """NoSeasonEpisodeInfo with no name or extension
    """
    ep = NoSeasonEpisodeInfo(
        seriesname = 'Scrubs',
        episodenumbers = [2],
        episodename = None,
        filename = None)

    assertEquals(
        ep.generate_filename(),
        'Scrubs - [02]')


def test_datedepisode_no_name_no_ext():
    # type: () -> None
    """DatedEpisodeInfo with no name or extension
    """
    ep = DatedEpisodeInfo(
        seriesname = 'Scrubs',
        episodenumbers = [datetime.date(2010, 11, 23)],
        episodename = None,
        filename = None)

    assertEquals(
        ep.generate_filename(),
        'Scrubs - [2010-11-23]')


def test_no_series_number():
    # type: () -> None
    """Episode without season number
    """
    ep = NoSeasonEpisodeInfo(
        seriesname = 'Scrubs',
        episodenumbers = [2],
        episodename = ['My Mentor'],
        filename = None)

    assertEquals(
        ep.generate_filename(),
        'Scrubs - [02] - My Mentor')


def test_episode_number_formatting():
    # type: () -> None
    from tvnamer.data import format_episode_name
    fmt = "%(epname)s (%(episodemin)s-%(episodemax)s)"
    joiner = ", "

    # Simple cases
    assert format_episode_name(['A test'], joiner, fmt) == 'A test'
    assert format_episode_name(['A test (1)'], joiner, fmt) == 'A test (1)'
    assert format_episode_name(['A test (1)', 'A test (2)'], joiner, fmt) == 'A test (1-2)'
    assert format_episode_name(['A test (1)', 'A test (2)', 'A test (3)'], joiner, fmt) == 'A test (1-3)'

    # Inconsistent episode names
    assert format_episode_name(['A test (1)', "Weirdness (2)"], joiner, fmt) == 'A test (1), Weirdness (2)'

    # Skip incomplete sequences
    assert format_episode_name(['A test (1)', 'A test (8)'], joiner, fmt) == 'A test (1), A test (8)'

    # Skip if numbers are duplicated
    assert format_episode_name(['A test (1)', 'A test (1)'], joiner, fmt) == 'A test (1), A test (1)'

    # First episode can miss name
    assert format_episode_name(['A test', 'A test (2)', 'A test (3)'], joiner, fmt) == 'A test (1-3)'

    # Different format options
    assert format_episode_name(['Yep', 'Thing'], "!", fmt) == 'Yep!Thing'
    assert format_episode_name(['A test (1)', 'A test (2)', 'A test (3)'], ",", "%(epname)s (%(episodemin)s to %(episodemax)s)") == 'A test (1 to 3)'
