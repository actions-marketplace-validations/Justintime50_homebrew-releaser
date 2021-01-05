import requests
import subprocess
import os
import re


BASE_URL = 'https://api.github.com'
HEADERS = {
    'accept': 'application/vnd.github.v3+json',
    'agent': 'Homebrew Releaser'
}
SUBPROCESS_TIMEOUT = 30
TAR_ARCHIVE = 'tar_archive.tar.gz'

# GitHub Action Env Variables
GITHUB_TOKEN = os.getenv('INPUT_GITHUB_TOKEN')
OWNER = os.getenv('INPUT_OWNER')
OWNER_EMAIL = os.getenv('INPUT_OWNER_EMAIL', 'homebrew-releaser@example.com')
REPO = os.getenv('INPUT_REPO')
INSTALL = os.getenv('INPUT_INSTALL')
TEST = os.getenv('INPUT_TEST')  # Optional env variable
HOMEBREW_TAP = os.getenv('INPUT_HOMEBREW_TAP')
HOMEBREW_FORMULA_FOLDER = os.getenv('INPUT_HOMEBREW_FORMULA_FOLDER')


def run_github_action():
    """Runs the GitHub Action and checks for required env variables
    """
    # TODO: Add logging
    check_required_env_variables()
    repository = make_get_request(f'{BASE_URL}/repos/{OWNER}/{REPO}', False).json()

    latest_release = make_get_request(f'{BASE_URL}/repos/{OWNER}/{REPO}/releases/latest', False).json()
    version = latest_release['name']
    tar_url = f'https://github.com/{OWNER}/{REPO}/archive/{version}.tar.gz'

    get_latest_tar_archive(tar_url)
    checksum = get_checksum(TAR_ARCHIVE)

    template = generate_formula(
        OWNER,
        REPO,
        version,
        repository,
        checksum,
        INSTALL,
        tar_url,
        TEST,
    )
    write_file(f'new_{repository["name"]}.rb', template, 'w')

    commit_formula(OWNER, OWNER_EMAIL, REPO, version)
    print(f'Successfully released {version} of {REPO} to {HOMEBREW_TAP}!')


def check_required_env_variables():
    """Checks that all required env variables are set
    """
    required_env_variables = [
        GITHUB_TOKEN,
        OWNER,
        OWNER_EMAIL,
        REPO,
        INSTALL,
        HOMEBREW_TAP,
        HOMEBREW_FORMULA_FOLDER
    ]
    for env_variable in required_env_variables:
        if not env_variable:
            raise SystemExit(
                'You must provide all necessary environment variables. Please reference the documentation.'  # noqa
            )
    return True


def make_get_request(url, stream=False):
    """Make a GET HTTP request
    """
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            stream=stream
        )
    except requests.exceptions.RequestException as error:
        raise SystemExit(error)
    return response


def get_latest_tar_archive(url):
    """Download the latest tar archive
    """
    response = make_get_request(url, True)
    write_file(TAR_ARCHIVE, response.content, 'wb')


def write_file(filename, content, mode='w'):
    """Writes content to a file
    """
    try:
        with open(filename, mode) as f:
            f.write(content)
    except Exception as error:
        raise SystemExit(error)


def get_checksum(tar_file):
    """Gets the checksum of a file
    """
    # TODO: Create and upload a `checksums.txt` file to the release for the zip and tar archives
    try:
        output = subprocess.check_output(
            f'shasum -a 256 {tar_file}',
            stdin=None,
            stderr=None,
            shell=True,
            timeout=SUBPROCESS_TIMEOUT
        )
        checksum = output.decode().split()[0]
        checksum_file = output.decode().split()[1]  # TODO: Use this to craft the `checksums.txt` file  # noqa
    except subprocess.TimeoutExpired as error:
        raise SystemExit(error)
    except subprocess.CalledProcessError as error:
        raise SystemExit(error)
    return checksum


def generate_formula(username, repo_name, version, repository, checksum, install, tar_url, test):  # noqa
    """Generates the formula file for Homebrew

    We attempt to ensure generated formula will pass `brew audit --strict` if given correct inputs:
    - Proper class name
    - 80 character or less desc field
    - Present homepage
    - URL points to the tar file
    - Checksum matches the url archive
    - Proper installable binary
    - Test is included
    """
    # TODO: Add the ability to add a `depends_on` block
    # TODO: Do we need to allow the user to specify the bottle instructions?
    repo_name_length = len(repo_name) + 2  # We add 2 here to offset for spaces and a add buffer
    max_desc_field_length = 80
    description_length = max_desc_field_length - repo_name_length

    test = f"""
  test do
    {test.strip()}
  end
end
""" if test else 'end'

    template = f"""# frozen_string_literal: true
# This file was generated by Homebrew Releaser. DO NOT EDIT.
class {re.sub(r'[-_. ]+', '', repo_name.title())} < Formula
  desc "{repository['description'][:description_length].strip()}"
  homepage "https://github.com/{username}/{repo_name}"
  url "{tar_url}"
  sha256 "{checksum}"
  license "{repository['license']['spdx_id']}"
  bottle :unneeded

  def install
    {install.strip()}
  end
{test}
"""
    return template


def commit_formula(owner, owner_email, repo, version):
    """Commits the new formula to the remote Homebrew tap repo.

    1) Set global git config so this automated process can be attached to a user
    2) Clone the Homebrew tap repo
    3) Move our generated formula to the repo
    4) Commit and push the updated formula file to the repo
    """
    try:
        output = subprocess.check_output(
            (
                f'git config --global user.name "{owner}" && '
                f'git config --global user.email {owner_email} && '
                f'git clone --depth=5 https://{GITHUB_TOKEN}@github.com/{owner}/{HOMEBREW_TAP}.git && '
                f'mv new_{repo}.rb {HOMEBREW_TAP}/{HOMEBREW_FORMULA_FOLDER}/{repo}.rb && '
                f'cd {HOMEBREW_TAP} && '
                f'git add {HOMEBREW_FORMULA_FOLDER}/{repo}.rb && '
                f'git commit -m "Brew formula update for {repo} version {version}" && '
                f'git push https://{GITHUB_TOKEN}@github.com/{owner}/{HOMEBREW_TAP}.git'
            ),
            stdin=None,
            stderr=None,
            shell=True,
            timeout=SUBPROCESS_TIMEOUT
        )
    except subprocess.TimeoutExpired as error:
        raise SystemExit(error)
    except subprocess.CalledProcessError as error:
        raise SystemExit(error)
    return output


def main():
    run_github_action()


if __name__ == '__main__':
    main()
