# Changelog

## [0.2.0](https://github.com/maelbel/skillspector-web/compare/v0.1.1...v0.2.0) (2026-09-05)


### Features

* add Claude CLI as a server-wide LLM provider option ([#6](https://github.com/maelbel/skillspector-web/issues/6)) ([931dd26](https://github.com/maelbel/skillspector-web/commit/931dd269a49ffd261591feb8a5648a061f8d2be1))
* add interactive `pnpm setup` wizard ([#7](https://github.com/maelbel/skillspector-web/issues/7)) ([c56e6f8](https://github.com/maelbel/skillspector-web/commit/c56e6f8e67c010a70752ea5c5df2923691b043d7))
* add persistent scan history ([#8](https://github.com/maelbel/skillspector-web/issues/8)) ([b57cef1](https://github.com/maelbel/skillspector-web/commit/b57cef1f2660c4b49b5c392ef2ca20942aa42ae4))
* auto-delete old scans, configurable live from the admin page ([#14](https://github.com/maelbel/skillspector-web/issues/14)) ([aa1c1d7](https://github.com/maelbel/skillspector-web/commit/aa1c1d71eb5851219edd565da20acee16dd54e06))
* history card UX improvements + open scan deletion ([#13](https://github.com/maelbel/skillspector-web/issues/13)) ([0c22c89](https://github.com/maelbel/skillspector-web/commit/0c22c8959f09f04a88aec70bece4f9a066a30719))
* let users bring their own LLM API key per scan ([#5](https://github.com/maelbel/skillspector-web/issues/5)) ([d4c4369](https://github.com/maelbel/skillspector-web/commit/d4c4369af38e006aaf15a85402d1d3a2e1cae5ca))
* live scan progress (logs + step progress bar) ([#9](https://github.com/maelbel/skillspector-web/issues/9)) ([6a4016a](https://github.com/maelbel/skillspector-web/commit/6a4016aedcb0d698b97b2e813be1de25c69278e1))
* rate limit admin-token attempts (brute-force protection) ([#17](https://github.com/maelbel/skillspector-web/issues/17)) ([f691835](https://github.com/maelbel/skillspector-web/commit/f691835c095f9a80ede5b6bdac5d79591a97e7d7))
* rate limit the scan endpoint per client ([#12](https://github.com/maelbel/skillspector-web/issues/12)) ([114aa1f](https://github.com/maelbel/skillspector-web/commit/114aa1f4f51f93da47f561f69a73c93e169458f2))


### Bug Fixes

* point header GitHub link at this repo, not skillspector's ([#3](https://github.com/maelbel/skillspector-web/issues/3)) ([ca189b9](https://github.com/maelbel/skillspector-web/commit/ca189b919e520fc197d090773fea55adcb5d8b03))
* retention sweep loop no longer dies silently on error ([#15](https://github.com/maelbel/skillspector-web/issues/15)) ([b9a22cf](https://github.com/maelbel/skillspector-web/commit/b9a22cfaa1659ac650eac8bf1e7b50832a4eba50))

## [0.1.1](https://github.com/maelbel/skillspector-web/compare/v0.1.0...v0.1.1) (2026-09-03)


### Bug Fixes

* make backend .env.local optional in docker-compose.yml ([103c0a3](https://github.com/maelbel/skillspector-web/commit/103c0a31bcb73b99914a96d5b306bdcf9a862514))
