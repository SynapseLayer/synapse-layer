# SDK TypeScript — Source Gap Notice

**Status:** dist/ recuperado do npm@1.2.0 (2026-07-28).
**Gap:** O código-fonte `.ts` que gerou este dist/ não foi commitado no working tree local.

## Evidência
- npm `synapse-layer@1.2.0`: dist/ com 8 arquivos compilados (26168 bytes, 18 files).
- Commit local: `e75925e feat(sdk): add TypeScript SDK v1.2.0` — apenas README+package.json.
- Hipótese: build foi feito em outra máquina/estado e publicado sem commit do src/.

## Próximos Passos (Roadmap)
1. Reconstruir `src/` a partir do `dist/` (decompilação assistida por IA).
2. Ou reescrever `src/` do zero alinhado ao `dist/` existente como contrato de API.
3. Publicar `synapse-layer@2.4.6` após reconstrução e testes.

## Versão Canônica
- Local `package.json`: version `2.4.6` (alinhamento canônico Forge).
- npm latest: `1.2.0` (bump canônico pendente de publicação).
