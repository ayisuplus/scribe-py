"""题材匹配 — 根据用户输入推荐作家组合"""

from __future__ import annotations


class WriterRouter:
    """根据用户输入推荐最相关的作家组合"""

    WRITER_GENRES: dict[str, set[str]] = {
        "jiulufeixiang": {"仙侠", "言情", "古装", "轻喜剧", "虐心"},
        "mo-xiang-tong-xiu": {"仙侠", "耽美", "群像", "反派设计", "暗黑"},
        "priest": {"科幻", "蒸汽朋克", "西幻", "刑侦", "悬疑", "反乌托邦", "深度"},
        "san-san": {"纯文学", "短篇", "现实主义", "哲学", "女性"},
        "liu-cui-hu": {"都市", "职场", "情感", "现实题材", "女性"},
        "mei-shi-niang": {"现实题材", "历史", "小人物", "长篇", "温暖"},
    }

    COMBO_SUGGESTIONS: dict[str, list[str]] = {
        "仙侠": ["jiulufeixiang", "mo-xiang-tong-xiu"],
        "都市": ["liu-cui-hu", "mei-shi-niang"],
        "现实": ["mei-shi-niang", "san-san", "liu-cui-hu"],
        "言情": ["jiulufeixiang", "liu-cui-hu"],
        "纯文学": ["san-san", "mei-shi-niang"],
        "科幻": ["priest", "mo-xiang-tong-xiu"],
        "悬疑": ["priest", "liu-cui-hu"],
        "西幻": ["priest", "mo-xiang-tong-xiu"],
    }

    def recommend(self, topic: str, user_text: str | None = None) -> list[str]:
        """根据主题和文本内容推荐作家ID列表"""
        scores: dict[str, int] = {wid: 0 for wid in self.WRITER_GENRES}
        combined = topic + (user_text or "")

        for wid, genres in self.WRITER_GENRES.items():
            for genre in genres:
                if genre in combined:
                    scores[wid] += 1

        ranked = sorted(scores.items(), key=lambda x: -x[1])
        top = [wid for wid, score in ranked if score > 0][:3]

        # 兜底：至少选2位
        if len(top) < 2:
            top = [wid for wid, _ in ranked[:2]]

        return top
