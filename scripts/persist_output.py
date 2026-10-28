"""Publish only the generated snapshot, with an exact lease on ocean-output."""
import argparse
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

BRANCH = 'refs/heads/ocean-output'


def persist(repo, output, remote='origin', expected=None):
    repo, output = Path(repo).resolve(), Path(output).resolve()
    if not (output / 'public').is_dir() or not (output / 'state').is_dir():
        raise ValueError('Generated public and state directories are required')
    def git(*args, env=None):
        return subprocess.check_output(['git', '-C', str(repo), *args], env=env, stderr=subprocess.PIPE).decode().strip()
    git_dir = git('rev-parse', '--absolute-git-dir')
    state = output / 'state'
    history_path = state / 'publication-history.json'
    previous_history = history_path.read_bytes() if history_path.exists() else None
    history = json.loads(previous_history) if previous_history is not None else []
    history.append({'published_at': datetime.now(timezone.utc).isoformat(),
                    'source_commit': git('rev-parse', 'HEAD'), 'previous_output_commit': expected,
                    'run_id': os.environ.get('GITHUB_RUN_ID'),
                    'retention': json.loads((state / 'retention.json').read_text()) if (state / 'retention.json').exists() else None})
    history_path.write_text(json.dumps(history[-32:], indent=2) + '\n')
    try:
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, GIT_INDEX_FILE=str(Path(tmp) / 'index'),
                       GIT_AUTHOR_NAME='github-actions[bot]', GIT_COMMITTER_NAME='github-actions[bot]',
                       GIT_AUTHOR_EMAIL='41898282+github-actions[bot]@users.noreply.github.com',
                       GIT_COMMITTER_EMAIL='41898282+github-actions[bot]@users.noreply.github.com')
            def staged(*args):
                return git('--git-dir', git_dir, '--work-tree', str(output), *args, env=env)
            staged('read-tree', '--empty')
            # Source, preference labels and unrelated output directories cannot enter the snapshot.
            staged('add', '--all', '--', str(output / 'public'), str(output / 'state'))
            tree = staged('write-tree')
            commit = staged('commit-tree', tree, '-m', 'Publish bounded ocean snapshot')
            # No parent keeps old generated PNG blobs out of reachable branch history.
            # The exact lease rejects a concurrent update instead of overwriting it.
            git('push', '--force-with-lease=' + BRANCH + ':' + (expected or ''), remote, commit + ':' + BRANCH)
            return commit
    except Exception:
        if previous_history is None:
            history_path.unlink(missing_ok=True)
        else:
            history_path.write_bytes(previous_history)
        raise



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='output')
    args = parser.parse_args()
    expected = subprocess.run(['git', 'rev-parse', '--verify', 'refs/remotes/origin/ocean-output'], capture_output=True, text=True)
    if expected.returncode not in (0, 128):
        raise RuntimeError('Cannot determine restored output branch head')
    try:
        print(persist(Path.cwd(), args.output, expected=expected.stdout.strip() if expected.returncode == 0 else None))
    except subprocess.CalledProcessError as error:
        raise SystemExit('Generated snapshot was not published: ' + error.stderr.decode(errors='replace')[-3000:])


if __name__ == '__main__':
    main()
