"""YouTube Music API wrapper using ytmusicapi."""
from ytmusicapi import YTMusic


class YTMusicAPI:
    def __init__(self):
        self._client = YTMusic()

    def search_songs(self, query: str, limit: int = 25) -> list[dict]:
        """Search for songs and return a list of track dicts."""
        raw = self._client.search(query, filter="songs", limit=limit)
        tracks = []
        for item in raw:
            if item.get("resultType") != "song":
                continue
            video_id = item.get("videoId")
            if not video_id:
                continue
            artists = ", ".join(a["name"] for a in item.get("artists", []) if a.get("name"))
            album_info = item.get("album") or {}
            tracks.append(
                {
                    "videoId": video_id,
                    "title": item.get("title") or "Unknown",
                    "artist": artists or "Unknown",
                    "album": album_info.get("name") or "",
                    "duration": item.get("duration") or "",
                }
            )
        return tracks
