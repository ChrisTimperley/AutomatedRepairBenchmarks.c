from typing import Iterator
import logging

from .api import APIClient
from .errors import UnexpectedAPIResponse
from ..core.bug import Bug
from ..core.coverage import TestSuiteCoverage


class BugManager(object):
    def __init__(self, api: APIClient) -> None:
        logging.basicConfig(level=logging.DEBUG)
        self.__logger = logging.getLogger('bug')
        self.__api = api

    def __getitem__(self, name: str) -> Bug:
        self.__logger.info("Fetching information for bug: %s", name)
        r = self.__api.get('bugs/{}'.format(name))

        if r.status_code == 200:
            return Bug.from_dict(r.json())
        if r.status_code == 404:
            self.__logger.info("Bug not found: %s", name)
            raise KeyError("no bug found with given name: {}".format(name))

        self.__logger.info("Unexpected API response when retrieving bug: %s", name)
        raise UnexpectedAPIResponse(r)

    def __iter__(self) -> Iterator[str]:
        """
        Returns an iterator over the names of the bugs registered with
        the server.
        """
        r = self.__api.get('bugs')

        if r.status_code == 200:
            names = r.json()
            assert isinstance(names, list)
            assert all(isinstance(n, str) for n in names)
            return names.__iter__()

        raise UnexpectedAPIResponse(r)

    def is_installed(self, bug: Bug) -> bool:
        """
        """
        r = self.__api.get('bugs/{}/installed'.format(bug.name))

        if r.status_code == 200:
            answer = r.json()
            assert isinstance(answer, bool)
            return answer

        # TODO bug not registered on server
        if r.status_code == 404:
            raise KeyError("no bug found with given name: {}".format(bug.name))

        raise UnexpectedAPIResponse(r)

    def coverage(self, bug: Bug) -> TestSuiteCoverage:
        r = self.__api.post('bugs/{}/coverage'.format(bug.name))

    def uninstall(self, bug: Bug) -> bool:
        r = self.__api.post('bugs/{}/uninstall'.format(bug.name))

    def upload(self, bug: Bug) -> bool:
        r = self.__api.post('bugs/{}/upload'.format(bug.name))

    def download(self, bug: Bug) -> bool:
        r = self.__api.post('bugs/{}/download'.format(bug.name))

    def build(self, bug: Bug):
        r = self.__api.post('bugs/{}/build'.format(bug.name))

        if r.status_code == 204:
            return
        if r.status_code == 200:
            raise errors.BugAlreadyBuilt(bug_id)
        # TODO: implement ImageBuildFailed.from_dict
        if r.status_code == 400:
            raise Exception("build failure")
        if r.status_code == 404:
          raise KeyError("no bug found with given name: {}".format(bug.name))

        raise UnexpectedAPIResponse(r)