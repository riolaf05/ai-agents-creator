# Python async: tips pratici

- Usa `asyncio.run(main())` come punto di ingresso top-level.
- Evita di mischiare loop diversi: se già dentro un loop, usa `await` direttamente.
- `asyncio.gather` per parallelizzare coroutine indipendenti.
- `asyncio.TaskGroup` (3.11+) è più robusto in caso di eccezioni.
- Per I/O di rete preferisci `httpx.AsyncClient` a `requests`.
- Attenzione al GIL: la concorrenza async accelera solo il codice I/O-bound,
  non quello CPU-bound. Per CPU usa `concurrent.futures.ProcessPoolExecutor`.
