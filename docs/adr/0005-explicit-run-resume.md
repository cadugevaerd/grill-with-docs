# Resumable runs and bounded stall recovery

O Gauntlet Loop persiste cada run, wave, lease, resultado e receipt no Project Store. Após 15 minutos sem progresso, o chat principal substitui uma vez o worker travado ou o watchdog relança uma vez o Loop no mesmo `run_id`; nova ocorrência bloqueia a run com diagnóstico. Fora dessa recuperação limitada, a continuidade exige retomada explícita e validada; apenas falhas transitórias classificadas recebem uma nova tentativa automática.
