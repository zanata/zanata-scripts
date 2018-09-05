#!/usr/bin/env python
# encoding: utf-8
"""ZanataRpmRepo -- Release package in dnf/yum repo

ZanataRpmRepo builds and Zanata RPM packages and upload
to the remote dnf/yum repository.

Requires:
    * docker
    * rsync
    * ssh

@author:     Ding-Yi Chen

@copyright:  2018 Red Hat Asia Pacific. All rights reserved.

@license:    LGPLv2+

@contact:    dchen@redhat.com
@deffield    updated: Updated
"""
from __future__ import absolute_import, division, print_function

import logging
import os
import sys

from ZanataArgParser import ZanataArgParser  # pylint: disable=E0401
from ZanataFunctions import GitHelper, SshHost, WORK_ROOT
from ZanataFunctions import mkdir_p, working_directory
from ZanataFunctions import exec_check_call, exec_check_output

try:
    # We need to import 'List' and 'Any' for mypy to work
    from typing import List, Any  # noqa: F401 # pylint: disable=unused-import
except ImportError:
    sys.stderr.write("python typing module is not installed" + os.linesep)

PROFILE = 0

LOCAL_DIR = os.path.join(WORK_ROOT, 'dnf', 'zanata')


class RpmRepoHost(SshHost):
    """Host that hosts Rpm Repo"""
    FEDORAPEOPLE_HOST = 'fedorapeople.org'

    def __init__(  # pylint: disable=too-many-arguments
            self, host=FEDORAPEOPLE_HOST,
            ssh_user=None, identity_file=None,
            remote_dir='/srv/repos/Zanata_Team/zanata',
            local_dir=LOCAL_DIR):
        super(RpmRepoHost, self).__init__(host, ssh_user, identity_file)
        self.remote_dir = remote_dir
        self.remote_host_dir = "%s:%s" % (self.user_host, self.remote_dir)
        self.local_dir = local_dir

    @classmethod
    def init_from_parsed_args(cls, args):
        """Init from command line arguments"""
        setattr(args, 'host', RpmRepoHost.FEDORAPEOPLE_HOST)
        return super(RpmRepoHost, cls).init_from_parsed_args(args)

    def pull(self):
        # type (str) -> None
        """Pull from remote directory
        """
        mkdir_p(self.local_dir)
        src_dir = os.path.join(self.remote_host_dir, '')
        logging.info("Pull from %s to %s", src_dir, self.local_dir)
        self.rsync(src_dir, self.local_dir, ['--delete'])

    def update_epel_repos(
            self, spec_file, version='auto',
            tarball_dir=None, dist_versions=None):
        """Update all EPEL repositories

        Args:
            spec_file (str): RPM spec file
            tarball_dir (str): Default to None.
                    Tarballs are downloaded to this directory.
                    If not specified, it downloads inside container,
                    which you cannot reused.
            dist_versions (List[str]): Defaults to ["7", "6"].
                    List of distrion versions to update.
        """
        if not dist_versions:
            dist_versions = ["7", "6"]
        for dist in dist_versions:
            logging.info("Update EL%s repo", dist)
            elrepo = ElRepo(dist, self.local_dir)
            elrepo.build_and_update(spec_file, version, tarball_dir)

    def push(self):
        # type (str) -> None
        """Push local files to remote directory
        """
        src_dir = os.path.join(self.local_dir, '')
        logging.info("Push from %s to %s", src_dir, self.remote_host_dir)
        self.rsync(src_dir, self.remote_host_dir, ['--delete'])

    def all(self, spec_file, version='auto'):
        """Run the full cycle

        Args:
            spec_file (str): RPM spec file
            version (str, optional): Defaults to 'auto'. New version of the
                    packages.
            dist_versions (List[str]): Defaults to ["7", "6"].
                    List of distrion versions to update.
        """
        self.pull()
        self.update_epel_repos(spec_file, version)
        self.push()


class ElRepo(object):  # pylint: disable=too-few-public-methods
    """A dnf/yum repository for Enterprisse Linux (EL)

    Each repository contains exactly one EPEL release (dist).
    Repository also contains RPMs for following arch:
    x86_64, i386, noarch, src
    """

    def __init__(self, dist_ver, local_dir=LOCAL_DIR):
        # type (str) -> None
        """New an ElRepo given distribution version

        Args:
            dist_ver (str): Distribution version like "7" or "6"
            loca_dir (str, optional): Defaults to LOCAL_DIR. Local directory
        """
        self.dist_ver = dist_ver
        self.local_dir = local_dir

    def build_and_update(self, spec_file, version=None, tarball_dir=None):
        # type (str, str, str) -> None
        """build RPM and update yum repo

        This program uses docker container,
        docker.io/zanata/centos-repo-builder,
        to update the repository.

        Args:
            spec_file (str): RPM spec file.
                    This should be related to local_dir.
            version (str, optional): Defaults to None.
            tarball_dir ([type], optional): Defaults to None.
                    tarballs are downloaded to this directory.
        """
        docker_cmd = '/usr/bin/docker'
        with working_directory(self.local_dir):
            volume_name = "zanata-el-%s-repo" % self.dist_ver
            vols = exec_check_output([
                    docker_cmd, 'volume', 'ls', '-q']).split('\n')
            if volume_name not in vols:
                exec_check_call([
                        docker_cmd, 'volume', 'create', '--name', volume_name])

            docker_run_cmd = [
                    docker_cmd, "run", "--rm", "--name",
                    "zanata-el-{}-builder".format(self.dist_ver),
                    "-v", "{}:/repo:Z".format(volume_name),
                    "-v", "{}:/repo_host_dir:Z".format(self.local_dir),
                    "-v", "{}:/output_dir:Z".format(self.local_dir)]

            if tarball_dir:
                docker_run_cmd += [
                        "-v", "%s:/rpmbuild/SOURCES:Z" % tarball_dir]

            docker_run_cmd += [
                    "docker.io/zanata/centos-repo-builder:{}".format(
                            self.dist_ver),
                    "-S", "/repo_host_dir/",
                    "-D", "/repo_host_dir/"]

            if version:
                if version == 'auto':
                    version = GitHelper.detect_remote_repo_latest_version(
                            'platform-',
                            'https://github.com/zanata/zanata-platform.git')
                logging.info(
                        "Update specfile %s to vesrsion %s ",
                        spec_file, version)
                docker_run_cmd += ['-u', version]

            docker_run_cmd.append(spec_file)
            exec_check_call(docker_run_cmd)


def main(argv=None):
    # type (dict) -> None
    """Run as command line program"""
    if not argv:
        argv = sys.argv[1:]
    parser = ZanataArgParser(__file__)
    parser.add_env('RPM_REPO_SSH_USER', dest='ssh_user')
    parser.add_env('RPM_REPO_SSH_IDENTITY_FILE', dest='identity_file')
    parser.add_methods_as_sub_commands(
            RpmRepoHost, "pull|push|update_.*|all")
    args = parser.parse_all(argv)
    parser.run_sub_command(args)


if __name__ == '__main__':
    if PROFILE:
        import cProfile
        import pstats
        profile_filename = 'ZanataRpmRepo_profile.txt'
        cProfile.run('main()', profile_filename)
        statsfile = open("profile_stats.txt", "wb")
        p = pstats.Stats(profile_filename, stream=statsfile)
        stats = p.strip_dirs().sort_stats('cumulative')
        stats.print_stats()
        statsfile.close()
        sys.exit(0)
    main()
