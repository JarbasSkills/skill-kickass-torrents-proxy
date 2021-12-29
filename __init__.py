from os.path import join, dirname

import requests
from ovos_plugin_common_play.ocp import MediaType, PlaybackType
from ovos_utils.parse import fuzzy_match
from ovos_workshop.skills.common_play import OVOSCommonPlaybackSkill, \
    ocp_search, ocp_play


class KickAssTorrentsSkill(OVOSCommonPlaybackSkill):
    def __init__(self):
        super(KickAssTorrentsSkill, self).__init__("KickAssTorrents")
        self.supported_media = [MediaType.GENERIC, MediaType.MOVIE,
                                MediaType.ADULT]
        self.skill_icon = join(dirname(__file__), "ui", "logo.png")

    @staticmethod
    def calc_score(phrase, torrent, media_type, idx=0, base_score=0):
        removes = ["WEBRip", "x265", "HDR", "DTS", "HD", "BluRay", "uhd",
                   "1080p", "720p", "BRRip", "XviD", "MP3", "2160p",
                   "h264", "AAC", "REMUX", "SDR", "hevc", "x264",
                   "REMASTERED", "KickAssTorrents", "SUBBED", "DVDRip"]
        removes = [r.lower() for r in removes]
        clean_name = torrent["title"].replace(".", " ").replace("-", " ")
        clean_name = " ".join([w for w in clean_name.split()
                               if w and w.lower() not in removes])
        score = base_score - idx
        score += fuzzy_match(phrase.lower(), clean_name) * 100
        if media_type == MediaType.MOVIE:
            score += 15
        return score

    @staticmethod
    def search_kickass(query):
        API_MAGNET = "https://kickass-api-unofficial.herokuapp.com/magnet"
        API_SEARCH = "https://kickass-api-unofficial.herokuapp.com/search"
        results = requests.get(API_SEARCH, params={"torrent": query}).json()
        for key, res in results.items():
            title = res['title']
            page_url = res['page_url']
            try:
                magnet = requests.get(API_MAGNET,
                                      params={"page_url": page_url}).json()
            except:
                continue  # rate limited ?
            magnet_link = magnet['magnet']
            yield {"title": title, "magnet": magnet_link}

    @ocp_search()
    def search_torrents(self, phrase, media_type):
        base_score = 0
        if self.voc_match(phrase, "torrent"):
            phrase = self.remove_voc(phrase, "torrent")
            base_score = 40

        idx = 0
        for torr in self.search_kickass(phrase):
            score = self.calc_score(phrase, torr, media_type, idx, base_score)
            yield {
                "title": torr["title"],
                "match_confidence": score,
                "media_type": MediaType.VIDEO,
                "uri": torr["magnet"],
                "playback": PlaybackType.SKILL,
                "skill_icon": self.skill_icon,
                "skill_id": self.skill_id
            }
            idx += 1

    @ocp_play()
    def stream_torrent(self, message):
        self.bus.emit(message.forward("skill.peerflix.play", message.data))


def create_skill():
    return KickAssTorrentsSkill()
