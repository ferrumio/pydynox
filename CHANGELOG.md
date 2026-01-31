# Changelog

All notable changes to this project will be documented in this file.
## [0.24.0] - 2026-01-31


### Documentation

- update changelog for v0.23.0 (#229)


### Features

- smart save - only send changed fields to DynamoDB (#232)
- adding model inheritance (#234)


### Refactoring

- rename hash e range key names
## [0.23.0] - 2026-01-30


### Documentation

- update changelog for v0.22.0 (#225)


### Features

- adding single table design (#226)


### Refactoring

- breaking change - rename hash e range key names (#228)
## [0.22.0] - 2026-01-29


### CI/CD

- bump actions/setup-python from 6.1.0 to 6.2.0 (#217)
- bump CodSpeedHQ/action from 4.7.0 to 4.8.2 (#219)
- bump github/codeql-action from 4.31.10 to 4.32.0 (#216)
- bump actions/checkout from 6.0.1 to 6.0.2 (#218)


### Documentation

- update changelog for v0.21.0 (#186)
- refactoring table operations async first (#197)
- refactoring s3 operations async first (#201)
- refactoring kms operations async first (#205)
- refactoring transaction operations async first (#209)
- refactoring batch operations async first (#213)
- refactoring all operations async first (#222)
- refactoring all operations async first


### Features

- add batch get support (#190)


### Refactoring

- start adding async as first design (#193)
- refactoring table operations async first (#196)
- refactoring s3 operations async first (#200)
- refactoring km operations async first (#204)
- refactoring transaction operations async first (#208)
- refactoring batch operations async first (#212)
- refactoring model/client operations async first (#221)


### Deps

- bump the rust-dependencies group with 2 updates (#220)
## [0.21.0] - 2026-01-22


### CI/CD

- bump actions/cache from 5.0.1 to 5.0.2 (#180)


### Documentation

- update changelog for v0.20.0 (#179)


### Features

- adding return values on failure (#181)
- adding transaction (#184)


### Refactoring

- Add `last_evaluated_key` parameter to GSI and LSI query (#185)


### Deps

- bump thiserror in the rust-dependencies group (#182)
## [0.20.0] - 2026-01-17


### Bug Fixes

- query pagination bug + add page_size parameter (#178)


### Documentation

- update changelog for v0.19.0 (#176)
## [0.19.0] - 2026-01-16


### Documentation

- update changelog for v0.18.0 (#174)


### Features

- add support for LSI (#175)
## [0.18.0] - 2026-01-16


### CI/CD

- bump CodSpeedHQ/action from 4.5.2 to 4.7.0 (#169)


### Docs

- add boto3 migration (#165)
- add annoucement (#167)


### Documentation

- update changelog for v0.17.0 (#163)


### Feat

- add async gsi query (#168)


### Refactoring

- fix type check issues (#171)
- unify all aws config clients (#173)


### Deps

- bump the rust-dependencies group across 1 directory with 8 updates (#170)
## [0.17.0] - 2026-01-15


### CI/CD

- bump actions/checkout from 4.2.2 to 6.0.1 (#149)
- bump astral-sh/setup-uv from 6.0.1 to 7.2.0 (#150)
- bump github/codeql-action from 3.28.19 to 4.31.10 (#151)
- bump softprops/action-gh-release from 2.2.1 to 2.5.0 (#148)


### Documentation

- update changelog for v0.16.0 (#146)


### Features

- adding testing feature (#147)
- add projection fields (#153)
- add KMS metrics (#159)
- add S3 metrics to Model observability (#162)


### Refactor

- clean the tests (#161)


### Refactoring

- add class methods instead of instance attributes (#154)
## [0.16.0] - 2026-01-10


### CI/CD

- bump actions/download-artifact from 4.3.0 to 7.0.0 (#139)
- bump actions/setup-python from 5.6.0 to 6.1.0 (#137)
- bump actions/upload-artifact from 4.6.2 to 6.0.0 (#135)


### Documentation

- update changelog for v0.15.0 (#141)


### Features

- adding OTEL (#143)
- add `as_dict` parameter to skip Model instantiation (#144)
- adding table operations to model (#145)
## [0.15.0] - 2026-01-09


### CI/CD

- replace mypy with ty (#128)
- create examples test workflow (#132)
- bump actions/cache from 4.2.3 to 5.0.1 (#138)
- bump CodSpeedHQ/action from 3.5.0 to 4.5.2 (#136)


### Features

- add parallel scan (#130)


### Miscellaneous

- refactor python code (#134)
## [0.14.0] - 2026-01-07


### CI/CD

- add prebuilt wheels dists (#24)
- add memray tests + fix codspeed (#80)
- add scorecard (#96)
- add scorecard
- bump actions/cache from 4.3.0 to 5.0.1 (#105)
- bump astral-sh/setup-uv from 4.2.0 to 7.1.6 (#103)
- bump actions/checkout from 4.3.1 to 6.0.1 (#104)
- bump actions/setup-python from 5.6.0 to 6.1.0 (#106)
- bump codecov/codecov-action from 4.6.0 to 5.5.2 (#107)
- bump codecov/codecov-action from 5.4.3 to 5.5.2 (#118)
- bump PyO3/maturin-action from 1.48.1 to 1.49.4 (#119)
- bump ossf/scorecard-action from 2.4.1 to 2.4.3 (#117)
- bump actions/upload-pages-artifact from 3.0.1 to 4.0.0 (#116)
- bump pypa/gh-action-pypi-publish from 1.12.4 to 1.13.0 (#115)


### Documentation

- adding genai guidance (#46)
- add agentic examples (#109)
- adding api reference (#121)


### Features

- improving error messages (#19)
- add support for ORM Model (#22)
- add support for Pydantic integration (#23)
- add table management methods to DynamoDBClient (#25)
- adding TTL attribute (#29)
- adding Rate Limit feature (#31)
- adding lifecycle rules (#34)
- adding lifecycle rules (#35)
- add CompressedAttribute for automatic text compression (#37)
- adding encryption field (#39)
- adding item size calculator (#41)
- add ORM-style conditions (#50)
- add atomic operations support (#52)
- add JSONAttribute, EnumAttribute, DatetimeAttribute, and Set types (#54)
- add observability (#56)
- add support for GSI index (#58)
- add async support (#60)
- add consistent read (#62)
- add generators (#67)
- add dataclass integration (#69)
- add query class (#72)
- add PartiQL support (#76)
- add optimistic lock (#77)
- add full auth chain (#82)
- add scan (#83)
- add s3file attribute (#84)
- add multi-attribute GSI keys support (Nov 2025 DynamoDB feature) (#89)
- add benchmark infra with CloudWatch dashboard (#93)
- add update_by_key and delete_by_key static methods (#108)
- adding hot partition support (#124)


### Miscellaneous

- rename dynamoclient (#21)
- add analytics (#71)
- improve CI (#111)


### Refactoring

- organize imports with namespaces (#27)
- replace class Meta with ModelConfig (#44)
- modernize python code (#48)
- use data key instead of encrypt operation (#110)


### Deps

- bump the rust-dependencies group with 3 updates (#102)

