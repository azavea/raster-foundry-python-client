---
name: Release
about: When ready to cut a release
title: Release X.Y.Z
labels: ''
assignees: ''

---

- [ ] Create release branch:
```bash
$ git flow release start X.Y.Z
```
- [ ] Edit `setup.py` to reflect the version of this release
- [ ] Bump spec version (if applicable)
- [ ] Rotate `CHANGELOG.rst`:
* copy everything from unreleased into a new section for the release number you're working on. This should include a link to the tag in GitHub
* remove unused sections, e.g., if there are no security changes
* delete everything in the current unreleased section
* create a fresh unreleased section at the top of the changelog
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
