# Changelog

## [1.1.1](https://github.com/maelbel/skillspector-web/compare/v1.1.0...v1.1.1) (2026-09-27)


### Bug Fixes

* read backend/.env.local when running the API without Docker ([#35](https://github.com/maelbel/skillspector-web/issues/35)) ([ae8bca5](https://github.com/maelbel/skillspector-web/commit/ae8bca599e7b37858aa4db1bfb3f30c0eb673cd6))


### Documentation

* rewrite the README and add contributing and security guides ([#37](https://github.com/maelbel/skillspector-web/issues/37)) ([41d594e](https://github.com/maelbel/skillspector-web/commit/41d594eb885841dedc521a5daa3f8c550a5989b7))

## [1.1.0](https://github.com/maelbel/skillspector-web/compare/v1.0.0...v1.1.0) (2026-09-27)


### Features

* add a favicon ([#34](https://github.com/maelbel/skillspector-web/issues/34)) ([5346fca](https://github.com/maelbel/skillspector-web/commit/5346fcab4ec760dc1c96eaf78450979523ed3428))
* home page UX overhaul ([#33](https://github.com/maelbel/skillspector-web/issues/33)) ([8478827](https://github.com/maelbel/skillspector-web/commit/84788278beaea6fff843785983be07aab3312efe))


### Bug Fixes

* cap the number of queued scans ([#23](https://github.com/maelbel/skillspector-web/issues/23)) ([424d4f7](https://github.com/maelbel/skillspector-web/commit/424d4f74050fa09d7ee904465dac67e7ee524b38))
* capture scan logs emitted from LangGraph worker threads ([#30](https://github.com/maelbel/skillspector-web/issues/30)) ([af6ac99](https://github.com/maelbel/skillspector-web/commit/af6ac99942b58590df88136b4123ee7ae0334cd5))
* compare the admin token in constant time ([#27](https://github.com/maelbel/skillspector-web/issues/27)) ([7e3c96b](https://github.com/maelbel/skillspector-web/commit/7e3c96b72efd4b6b4d1a389a83c7ff79746f568d))
* derive the rate-limit client IP from a trusted hop only ([#22](https://github.com/maelbel/skillspector-web/issues/22)) ([6360c37](https://github.com/maelbel/skillspector-web/commit/6360c375a6d677292eacaa476d308e8c492f7e85))
* drop the release-as pin and keep every version string in sync ([#26](https://github.com/maelbel/skillspector-web/issues/26)) ([c96fae8](https://github.com/maelbel/skillspector-web/commit/c96fae84ecf1a75e0be33cea1b12b109481ad1bb))
* keep pending and running scans out of the retention sweep ([#29](https://github.com/maelbel/skillspector-web/issues/29)) ([4f09ed6](https://github.com/maelbel/skillspector-web/commit/4f09ed64294489d0abb25e180a516eb04ba6a6e2))
* mark scans interrupted by an API restart as failed ([#24](https://github.com/maelbel/skillspector-web/issues/24)) ([675684c](https://github.com/maelbel/skillspector-web/commit/675684cbecae54d9eebb079c32b287a064f8d139))
* stop /health from mutating os.environ during scans ([#21](https://github.com/maelbel/skillspector-web/issues/21)) ([bf30f85](https://github.com/maelbel/skillspector-web/commit/bf30f8584b8d0af6cea155f17d5eb705ce2a81c0))
* URL-encode the scan id when proxying to the backend ([#28](https://github.com/maelbel/skillspector-web/issues/28)) ([c27b835](https://github.com/maelbel/skillspector-web/commit/c27b835d7ee7789be89d5f888a079121caa35e1e))

## [1.0.0](https://github.com/maelbel/skillspector-web/compare/v0.1.1...v1.0.0) (2026-09-05)


### Features

* add Claude CLI as a server-wide LLM provider option ([#6](https://github.com/maelbel/skillspector-web/issues/6)) ([931dd26](https://github.com/maelbel/skillspector-web/commit/931dd269a49ffd261591feb8a5648a061f8d2be1))
* add interactive `pnpm setup` wizard ([#7](https://github.com/maelbel/skillspector-web/issues/7)) ([c56e6f8](https://github.com/maelbel/skillspector-web/commit/c56e6f8e67c010a70752ea5c5df2923691b043d7))
* add persistent scan history ([#8](https://github.com/maelbel/skillspector-web/issues/8)) ([b57cef1](https://github.com/maelbel/skillspector-web/commit/b57cef1f2660c4b49b5c392ef2ca20942aa42ae4))
* auto-delete old scans, configurable live from the admin page ([#14](https://github.com/maelbel/skillspector-web/issues/14)) ([aa1c1d7](https://github.com/maelbel/skillspector-web/commit/aa1c1d71eb5851219edd565da20acee16dd54e06))
* branded error page and active nav state ([#18](https://github.com/maelbel/skillspector-web/issues/18)) ([7636664](https://github.com/maelbel/skillspector-web/commit/7636664c339fe125352d972b07496bae21b802e8))
* filterable, collapsible, groupable findings list ([#19](https://github.com/maelbel/skillspector-web/issues/19)) ([a047bea](https://github.com/maelbel/skillspector-web/commit/a047bea8afbc91f2a862611768d5b31213216c1e))
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
