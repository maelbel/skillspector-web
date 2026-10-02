# Changelog

## [2.0.0](https://github.com/maelbel/skillspector-web/compare/v1.1.1...v2.0.0) (2026-10-02)


### Features

* a clearer backoffice settings page ([#127](https://github.com/maelbel/skillspector-web/issues/127)) ([ef98550](https://github.com/maelbel/skillspector-web/commit/ef98550cb675884253b1f738db4a62597823e9cd))
* a GitHub Action that scans the skills a pull request changes ([#128](https://github.com/maelbel/skillspector-web/issues/128)) ([a3ba8a6](https://github.com/maelbel/skillspector-web/commit/a3ba8a67541ecf2eaa46dfaae5de5de22ff0d207)), closes [#75](https://github.com/maelbel/skillspector-web/issues/75)
* a simpler scan form ([#122](https://github.com/maelbel/skillspector-web/issues/122)) ([f1320f3](https://github.com/maelbel/skillspector-web/commit/f1320f3280771bb0103ba562b238a16bf05c0f10))
* a status badge showing a skill's latest verdict ([#129](https://github.com/maelbel/skillspector-web/issues/129)) ([e1544b0](https://github.com/maelbel/skillspector-web/commit/e1544b0ed9697a7faa7660172407b712ad382b21)), closes [#76](https://github.com/maelbel/skillspector-web/issues/76)
* add a deployment mode setting (self_hosted | hosted) ([#52](https://github.com/maelbel/skillspector-web/issues/52)) ([fc81f08](https://github.com/maelbel/skillspector-web/commit/fc81f08fc5172f84ba02b1daa96716916d9217a9)), closes [#40](https://github.com/maelbel/skillspector-web/issues/40)
* admin backoffice, email password reset and public sign-up ([#58](https://github.com/maelbel/skillspector-web/issues/58)) ([1bc10d6](https://github.com/maelbel/skillspector-web/commit/1bc10d664432c46235fdae2281b19795ef220f51))
* an Open Graph image for link previews ([#143](https://github.com/maelbel/skillspector-web/issues/143)) ([1188fd8](https://github.com/maelbel/skillspector-web/commit/1188fd8ddead033842c52497185534707b416db1)), closes [#87](https://github.com/maelbel/skillspector-web/issues/87)
* apply the baseline a skill ships, when the user opts in ([#141](https://github.com/maelbel/skillspector-web/issues/141)) ([3bcd5a9](https://github.com/maelbel/skillspector-web/commit/3bcd5a9d52d2aa25fa4179df11f9f1ef6f34da60)), closes [#110](https://github.com/maelbel/skillspector-web/issues/110)
* connect GitHub to scan private repositories ([#137](https://github.com/maelbel/skillspector-web/issues/137)) ([751e406](https://github.com/maelbel/skillspector-web/commit/751e4067883b576cee29c7ec770b3039522288d6))
* deploy production from releases, and main as preprod ([#106](https://github.com/maelbel/skillspector-web/issues/106)) ([dd05641](https://github.com/maelbel/skillspector-web/commit/dd056415b606a7667c7b85daf14f7987f64daac4))
* deploy to Vercel as one project with two services ([#62](https://github.com/maelbel/skillspector-web/issues/62)) ([98c67fc](https://github.com/maelbel/skillspector-web/commit/98c67fc17ffc0655197b4d092e2321ca47f7f386))
* export reports, and share a read-only link to a result ([#124](https://github.com/maelbel/skillspector-web/issues/124)) ([16cf318](https://github.com/maelbel/skillspector-web/commit/16cf318a07206a66d0036b42f8680e2be2d6c372))
* legal notice, privacy policy and terms of use ([#142](https://github.com/maelbel/skillspector-web/issues/142)) ([b05072d](https://github.com/maelbel/skillspector-web/commit/b05072db6199b80854bf8b7b0b0a14f68ea47164)), closes [#73](https://github.com/maelbel/skillspector-web/issues/73)
* monitoring and alerts, self-hosted and hosted ([#130](https://github.com/maelbel/skillspector-web/issues/130)) ([16e4b1c](https://github.com/maelbel/skillspector-web/commit/16e4b1c17f6d74e1811c6f6bcf1f0bb86843f6b1))
* more AI providers, and a model picker ([#113](https://github.com/maelbel/skillspector-web/issues/113)) ([87cba2a](https://github.com/maelbel/skillspector-web/commit/87cba2aa0c2238127209f607944dcd16ff907447))
* one verdict per skill in repositories holding several ([#111](https://github.com/maelbel/skillspector-web/issues/111)) ([5032fc4](https://github.com/maelbel/skillspector-web/commit/5032fc4debcc2cc427e938cc93a3e5657fa1c14f))
* optional authentication with local accounts ([#57](https://github.com/maelbel/skillspector-web/issues/57)) ([bf8bad2](https://github.com/maelbel/skillspector-web/commit/bf8bad2bd92b0e4b3483f12106b531cb98cd1e32))
* optionally follow a skill's external references ([#112](https://github.com/maelbel/skillspector-web/issues/112)) ([c57b5e4](https://github.com/maelbel/skillspector-web/commit/c57b5e41ad46332e91aef8215cf1044a42ac8256))
* per-user Claude keys, encrypted at rest ([#59](https://github.com/maelbel/skillspector-web/issues/59)) ([6998374](https://github.com/maelbel/skillspector-web/commit/699837439b05921138814b0b4b9de6ff415566be)), closes [#46](https://github.com/maelbel/skillspector-web/issues/46)
* per-user quota overrides ([#131](https://github.com/maelbel/skillspector-web/issues/131)) ([da1eaed](https://github.com/maelbel/skillspector-web/commit/da1eaed5b755226847374f8f88b51f374b52ba88)), closes [#79](https://github.com/maelbel/skillspector-web/issues/79)
* per-user scan quotas and a pause switch ([#63](https://github.com/maelbel/skillspector-web/issues/63)) ([b4acaee](https://github.com/maelbel/skillspector-web/commit/b4acaeeb3225853f6647edc64e59a0fd0a150823)), closes [#50](https://github.com/maelbel/skillspector-web/issues/50)
* personal API tokens for scripts and CI ([#126](https://github.com/maelbel/skillspector-web/issues/126)) ([f1a6df2](https://github.com/maelbel/skillspector-web/commit/f1a6df23d367ce863ecf9b3723a4ee6745853fe6))
* pluggable job runner with Vercel Queues for hosted mode ([#54](https://github.com/maelbel/skillspector-web/issues/54)) ([63b7a5d](https://github.com/maelbel/skillspector-web/commit/63b7a5d6b95e4f0954773184c256fb7fcfdb207e)), closes [#42](https://github.com/maelbel/skillspector-web/issues/42)
* pluggable scan log and progress store ([#55](https://github.com/maelbel/skillspector-web/issues/55)) ([c14a343](https://github.com/maelbel/skillspector-web/commit/c14a343f899c3c11d0821a45a77d33eae90023a4)), closes [#43](https://github.com/maelbel/skillspector-web/issues/43)
* pluggable scan storage with Postgres support ([#53](https://github.com/maelbel/skillspector-web/issues/53)) ([13e357d](https://github.com/maelbel/skillspector-web/commit/13e357d108418d4cb3ed478cd64512fc212aea52)), closes [#41](https://github.com/maelbel/skillspector-web/issues/41)
* rebuild the sandbox snapshot when the skillspector pin changes ([#105](https://github.com/maelbel/skillspector-web/issues/105)) ([54a57a4](https://github.com/maelbel/skillspector-web/commit/54a57a49cd1c5a625f6a7ce5db6a120977b8a0ed))
* redesign the frontend with an NVIDIA-inspired theme ([#38](https://github.com/maelbel/skillspector-web/issues/38)) ([47a1f39](https://github.com/maelbel/skillspector-web/commit/47a1f39a691ff06bc58bcaab8edaee8d54d14a75))
* rescan a target and show what changed since its last scan ([#123](https://github.com/maelbel/skillspector-web/issues/123)) ([3f07e82](https://github.com/maelbel/skillspector-web/commit/3f07e82ee992fa15ce7aa81f8898ff1f3d902aed)), closes [#69](https://github.com/maelbel/skillspector-web/issues/69)
* richer finding details ([#116](https://github.com/maelbel/skillspector-web/issues/116)) ([8ab345e](https://github.com/maelbel/skillspector-web/commit/8ab345e87e15fde95cb7a8349922899e83ee5225))
* robots.txt, a sitemap, noindex and metadata for search engines ([#145](https://github.com/maelbel/skillspector-web/issues/145)) ([1335de3](https://github.com/maelbel/skillspector-web/commit/1335de39a458dce42c1415d85d1911d876384045)), closes [#89](https://github.com/maelbel/skillspector-web/issues/89)
* run hosted scans in a Vercel Sandbox ([#56](https://github.com/maelbel/skillspector-web/issues/56)) ([00e3660](https://github.com/maelbel/skillspector-web/commit/00e3660cce70442ac215bdb10447e58e7b35cfb8)), closes [#44](https://github.com/maelbel/skillspector-web/issues/44)
* run the retention sweep from Vercel Cron in hosted mode ([#61](https://github.com/maelbel/skillspector-web/issues/61)) ([195fce5](https://github.com/maelbel/skillspector-web/commit/195fce53739944610adf1b609faf26ba58819ab4)), closes [#48](https://github.com/maelbel/skillspector-web/issues/48)
* say when the AI review didn't run or only partly ran ([#104](https://github.com/maelbel/skillspector-web/issues/104)) ([9cc2a84](https://github.com/maelbel/skillspector-web/commit/9cc2a84cf0823022dffeccf9e47b85ecd3913ac5))
* scan a skill uploaded from the browser ([#121](https://github.com/maelbel/skillspector-web/issues/121)) ([a8b4624](https://github.com/maelbel/skillspector-web/commit/a8b4624a9e38260320a26a6935ed19ea6fb04212)), closes [#68](https://github.com/maelbel/skillspector-web/issues/68)
* scan an MCP server's registry entry ([#119](https://github.com/maelbel/skillspector-web/issues/119)) ([22ad2f7](https://github.com/maelbel/skillspector-web/commit/22ad2f7113948d25e21ca5dd68c8bc2b1817e384)), closes [#102](https://github.com/maelbel/skillspector-web/issues/102)
* scan one folder of a repository from its /tree/ link ([#120](https://github.com/maelbel/skillspector-web/issues/120)) ([628b9be](https://github.com/maelbel/skillspector-web/commit/628b9be5bfec28c1f81e62b3243a52787844c008)), closes [#67](https://github.com/maelbel/skillspector-web/issues/67)
* self-hosted scans survive API restarts ([#134](https://github.com/maelbel/skillspector-web/issues/134)) ([4f82af0](https://github.com/maelbel/skillspector-web/commit/4f82af024444f4c1ea0f35a34db5ae73c940acde))
* server-wide skillspector analysis settings for operators ([#118](https://github.com/maelbel/skillspector-web/issues/118)) ([03e62f6](https://github.com/maelbel/skillspector-web/commit/03e62f69f453461c33680aa9acb22a4e7b8d0c15)), closes [#101](https://github.com/maelbel/skillspector-web/issues/101)
* shared rate limits, BotID and firewall rules for hosted mode ([#60](https://github.com/maelbel/skillspector-web/issues/60)) ([6a9fa6a](https://github.com/maelbel/skillspector-web/commit/6a9fa6a32b2063f19bb9cc4bac705bf8d62eed66)), closes [#47](https://github.com/maelbel/skillspector-web/issues/47)
* show the AI tokens each scan used ([#108](https://github.com/maelbel/skillspector-web/issues/108)) ([3a6e319](https://github.com/maelbel/skillspector-web/commit/3a6e3193f65d49856c33b8b7d9b8d32adcc13810))
* show the files a scan inspected ([#117](https://github.com/maelbel/skillspector-web/issues/117)) ([29f5652](https://github.com/maelbel/skillspector-web/commit/29f5652a97089cc76bc90a352f73c6970acb9f88))
* show what a scan couldn't inspect ([#107](https://github.com/maelbel/skillspector-web/issues/107)) ([48477cb](https://github.com/maelbel/skillspector-web/commit/48477cbc67e43e9bfa7f95acec49ef265075ce78))
* sort the scan history ([#125](https://github.com/maelbel/skillspector-web/issues/125)) ([df837fb](https://github.com/maelbel/skillspector-web/commit/df837fbffaa97dbf19044a42adb888abbe941e18))
* suppress accepted findings with a baseline ([#109](https://github.com/maelbel/skillspector-web/issues/109)) ([b257f69](https://github.com/maelbel/skillspector-web/commit/b257f69820eaf7ae9098c6a4f1c4998177e31eaa))
* Vercel Speed Insights on the hosted version ([#133](https://github.com/maelbel/skillspector-web/issues/133)) ([ad73b83](https://github.com/maelbel/skillspector-web/commit/ad73b8397eef6be419253881e9507bbce623208f)), closes [#81](https://github.com/maelbel/skillspector-web/issues/81)
* Vercel Web Analytics on the hosted version ([#132](https://github.com/maelbel/skillspector-web/issues/132)) ([af21ee0](https://github.com/maelbel/skillspector-web/commit/af21ee02924f7b354186e6921f4366a5ee4852a5)), closes [#80](https://github.com/maelbel/skillspector-web/issues/80)


### Bug Fixes

* BotID blocking every scan, and a snapshot deleted on creation ([#64](https://github.com/maelbel/skillspector-web/issues/64)) ([47ac4de](https://github.com/maelbel/skillspector-web/commit/47ac4de71272af63cb2a53bda658f8a85617a135))
* label the header menu entry Account ([#90](https://github.com/maelbel/skillspector-web/issues/90)) ([00c3acc](https://github.com/maelbel/skillspector-web/commit/00c3acc889ff5392be6bfeeeecea17284d834c17))
* scan code host file links as the raw file ([#65](https://github.com/maelbel/skillspector-web/issues/65)) ([2a3ca10](https://github.com/maelbel/skillspector-web/commit/2a3ca104b2e8b71f31f1ad787611eac9a03756f7)), closes [#51](https://github.com/maelbel/skillspector-web/issues/51)
* the in-progress scan quota holds under simultaneous submissions ([#136](https://github.com/maelbel/skillspector-web/issues/136)) ([19a6509](https://github.com/maelbel/skillspector-web/commit/19a6509ccddeb7355f8d63e1f766f582e56f5b89)), closes [#86](https://github.com/maelbel/skillspector-web/issues/86)
* the sandbox tests pass on their own, and CI runs the suite in random order ([#135](https://github.com/maelbel/skillspector-web/issues/135)) ([ab4d4a3](https://github.com/maelbel/skillspector-web/commit/ab4d4a307705f199062cc1498052fccdc9f2e8b0)), closes [#85](https://github.com/maelbel/skillspector-web/issues/85)
* the web dev container no longer runs out of memory or dumps core ([#144](https://github.com/maelbel/skillspector-web/issues/144)) ([f0da78a](https://github.com/maelbel/skillspector-web/commit/f0da78a1d34b1a68fcfad3c5f73b604f1efec863))


### Documentation

* a shorter README, with the reference material under docs/ ([#66](https://github.com/maelbel/skillspector-web/issues/66)) ([83489b0](https://github.com/maelbel/skillspector-web/commit/83489b0e464ef297cf55055175bb59d77f2bd126))
* refresh the README screenshots, and script them ([#146](https://github.com/maelbel/skillspector-web/issues/146)) ([b417d82](https://github.com/maelbel/skillspector-web/commit/b417d8220aa137711480a4611a9e8dd6f1894ff7)), closes [#83](https://github.com/maelbel/skillspector-web/issues/83)


### Miscellaneous

* release 2.0.0 ([#147](https://github.com/maelbel/skillspector-web/issues/147)) ([33199a3](https://github.com/maelbel/skillspector-web/commit/33199a374d9e586ce05260e459a38a00570287ce))

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
