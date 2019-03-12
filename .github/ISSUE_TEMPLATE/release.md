---
name: Release
about: When ready to cut a release
title: Release X.Y.Z
labels: 'release'
assignees: ''

---

- [ ] Create release branch:
```bash
$ git flow release start X.Y.Z
```
- [ ] Edit `setup.py` to reflect the version of this release
- [ ] Bump spec version (if applicable)
- [ ] Rotate `CHANGELOG.rst` (following [Keep a Changelog](https://keepachangelog.com/) principles)
- [ ] Ensure outstanding changes are committed:
```bash
$ git add .
$ git commit -m "X.Y.Z"
```
- [ ] Finalize and publish release branch:
```bash
$ git flow release finish X.Y.Z
$ git push origin develop
$ git checkout master
$ git push origin master
$ git push --tags
```
