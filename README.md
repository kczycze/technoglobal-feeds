# technoglobal-feeds

Świeże nagłówki dla researchu TechnoGLOBAL. GitHub Actions uruchamia `fetch_feeds.py` dwa razy dziennie
(ok. 6:40 i 15:10 czasu polskiego zimą; latem godzinę później względem czasu polskiego — cron jest w UTC)
i zapisuje `feeds/latest.json` (pełna lista) oraz `feeds/digest.json` (krótka lista dla researchu: bez giełdy, raportów rynkowych i marketingu, najświeższe pozycje na kategorię): nagłówki z ostatnich 30 h z Google News (8 kategorii, po angielsku), komunikaty
prasowe (Business Wire, PR Newswire, GlobeNewswire), nagłówki po polsku i kanał NASA.

Repozytorium zawiera wyłącznie publiczne nagłówki i linki — żadnych kluczy.
