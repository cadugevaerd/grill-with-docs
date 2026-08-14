# Opt-in project Gauntlet configuration

Cada projeto usa uma configuração versionada para limite de paralelismo, stall e mapeamento de Model Tiers por runtime. Sua criação valida antes o workflow V3 e o adapter Claude Code; só então o work item se torna apto a iniciar uma run. A configuração pode elevar tiers ou restringir capacidades, mas não reduz mínimos, amplia permissões nem remove o gate humano de `ship`; V2 continua manual e inalterado.
