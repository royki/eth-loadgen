# eth-loadgen

![Version: 0.1.0](https://img.shields.io/badge/Version-0.1.0-informational?style=flat-square) ![Type: application](https://img.shields.io/badge/Type-application-informational?style=flat-square) ![AppVersion: 1.0.0](https://img.shields.io/badge/AppVersion-1.0.0-informational?style=flat-square)

Minimal Helm chart for Ethereum Load Generator

## Values

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| command[0] | string | `"python3"` |  |
| command[1] | string | `"app.py"` |  |
| command[2] | string | `"--server"` |  |
| env.BLOCK_POLL_INTERVAL | string | `"1.0"` |  |
| env.METRICS_HOST | string | `"0.0.0.0"` |  |
| env.METRICS_PORT | string | `"9000"` |  |
| env.METRICS_WINDOW_PERIOD | string | `"20"` |  |
| env.PRIVATE_KEY | string | `""` |  |
| env.PYTHONUNBUFFERED | string | `"1"` |  |
| env.RPC_URL | string | `"http://geth-node-service.dev.svc.cluster.local:8545"` |  |
| env.SERVER_DURATION | string | `"300"` |  |
| env.SERVER_FUND_AMOUNT | string | `"1000"` |  |
| env.SERVER_GAS | string | `"21000"` |  |
| env.SERVER_LOAD_MODE | string | `"random"` |  |
| env.SERVER_NUM_ACCOUNTS | string | `"100"` |  |
| env.SERVER_TPS | string | `"5"` |  |
| env.SERVER_TX_INCREMENT | string | `"0.5"` |  |
| env.SERVER_TX_MAX | string | `"100"` |  |
| env.SERVER_TX_MIN | string | `"0.1"` |  |
| env.SERVER_TX_MODE | string | `"ascending"` |  |
| env.UTC_FILE_PATH | string | `""` |  |
| env.UTC_PASSWORD | string | `""` |  |
| image.name | string | `"eth-loadgen"` |  |
| image.pullPolicy | string | `"IfNotPresent"` |  |
| image.repository | string | `"royki/eth-loadgen"` |  |
| image.tag | string | `"v1.0.1"` |  |
| ingress.annotations."nginx.ingress.kubernetes.io/backend-protocol" | string | `"HTTP"` |  |
| ingress.annotations."nginx.ingress.kubernetes.io/proxy-body-size" | string | `"10m"` |  |
| ingress.annotations."nginx.ingress.kubernetes.io/proxy-buffering" | string | `"off"` |  |
| ingress.annotations."nginx.ingress.kubernetes.io/proxy-connect-timeout" | string | `"60"` |  |
| ingress.annotations."nginx.ingress.kubernetes.io/proxy-read-timeout" | string | `"3600"` |  |
| ingress.annotations."nginx.ingress.kubernetes.io/proxy-send-timeout" | string | `"3600"` |  |
| ingress.annotations."nginx.ingress.kubernetes.io/ssl-redirect" | string | `"false"` |  |
| ingress.enabled | bool | `false` |  |
| ingress.hosts[0].host | string | `"eth-loadgen.local"` |  |
| ingress.hosts[0].paths[0].backend.service.name | string | `"eth-loadgen-service"` |  |
| ingress.hosts[0].paths[0].backend.service.port.number | int | `9000` |  |
| ingress.hosts[0].paths[0].path | string | `"/"` |  |
| ingress.hosts[0].paths[0].pathType | string | `"Prefix"` |  |
| ingress.ingressClassName | string | `"nginx"` |  |
| keystore.data."UTC--2025-10-26T12-15-30.572257963Z--71562b71999873db5b286df957af199ec94617f7" | string | `"{\"address\":\"71562b71999873db5b286df957af199ec94617f7\",\"crypto\":{\"cipher\":\"aes-128-ctr\",\"ciphertext\":\"919f5d13ba21070d235e357fa0272d6e1a2bf93f6be54801a9f478a7b66f1d5e\",\"cipherparams\":{\"iv\":\"97083c4f8fb741a92af72d92ca00196d\"},\"kdf\":\"scrypt\",\"kdfparams\":{\"dklen\":32,\"n\":4096,\"p\":6,\"r\":8,\"salt\":\"24ceca351742e762a441f74593dc187117075c98dd19a29abd4cc6162ea985c7\"},\"mac\":\"127db5ecec20ffb1d2abc470ecf37c80fd91cd47bfa2fcdea057a345d5bf9359\"},\"id\":\"12bdc05a-aa9e-495d-876f-318995339070\",\"version\":3}\n"` |  |
| keystore.enabled | bool | `true` |  |
| keystore.name | string | `"eth-loadgen-keystore"` |  |
| keystore.type | string | `"configmap"` |  |
| livenessProbe.enabled | bool | `true` |  |
| livenessProbe.failureThreshold | int | `3` |  |
| livenessProbe.httpGet.path | string | `"/metrics"` |  |
| livenessProbe.httpGet.port | string | `"metrics"` |  |
| livenessProbe.initialDelaySeconds | int | `30` |  |
| livenessProbe.periodSeconds | int | `30` |  |
| livenessProbe.timeoutSeconds | int | `10` |  |
| metricsPort | int | `9000` |  |
| mode | string | `"server"` |  |
| readinessProbe.enabled | bool | `true` |  |
| readinessProbe.failureThreshold | int | `3` |  |
| readinessProbe.httpGet.path | string | `"/metrics"` |  |
| readinessProbe.httpGet.port | string | `"metrics"` |  |
| readinessProbe.initialDelaySeconds | int | `10` |  |
| readinessProbe.periodSeconds | int | `10` |  |
| readinessProbe.timeoutSeconds | int | `5` |  |
| replicaCount | int | `1` |  |
| resources.limits.cpu | string | `"500m"` |  |
| resources.limits.memory | string | `"512Mi"` |  |
| resources.requests.cpu | string | `"100m"` |  |
| resources.requests.memory | string | `"256Mi"` |  |
| service.ports[0].name | string | `"metrics"` |  |
| service.ports[0].port | int | `9000` |  |
| service.ports[0].targetPort | int | `9000` |  |
| service.type | string | `"ClusterIP"` |  |
| strategy.type | string | `"Recreate"` |  |
| tls | list | `[]` |  |
| volumes.keystore.mountPath | string | `"/app/keystores"` |  |
| volumes.keystore.name | string | `"keystore"` |  |

----------------------------------------------
Autogenerated from chart metadata using [helm-docs v1.5.0](https://github.com/norwoodj/helm-docs/releases/v1.5.0)
