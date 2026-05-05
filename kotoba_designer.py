#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════╗
║        KOTOBA DESIGNER  ─  言葉デザイナー            ║
║   Japanese Language Node-Based Learning System       ║
║   Built with PySide6                                 ║
╚══════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import sys
import json
import uuid
import math
import os
import random
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QStackedWidget,
    QGraphicsView, QGraphicsScene, QGraphicsItem,
    QGraphicsRectItem, QGraphicsPathItem, QGraphicsEllipseItem,
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QDialog, QLineEdit, QFormLayout,
    QMenu, QMessageBox, QFrame, QSizePolicy,
    QToolBar, QStatusBar,
    QTextEdit, QFileDialog, QScrollArea, QInputDialog,
    QGraphicsDropShadowEffect, QSplitter, QListWidget,
    QListWidgetItem, QAbstractItemView, QGraphicsItem
)
from PySide6.QtCore import (
    Qt, QPointF, QRectF, QSizeF, Signal, QObject,
    QTimer, QSize
)
from PySide6.QtGui import (
    QPainter, QPainterPath, QPen, QBrush, QColor, QFont,
    QLinearGradient, QRadialGradient, QKeySequence,
    QAction, QTransform, QCursor, QPixmap, QPalette,
    QFontMetrics, QIcon, QPolygonF, QPainterPathStroker
)

try:
    from Ai import LessonAI, BonsaiLLM, cute_reward_line
except Exception:
    LessonAI = None
    BonsaiLLM = None

    def cute_reward_line():
        return "よくできました!"

try:
    from voicevox.voicevox_engine import VoicevoxEngine, SynthParams
except Exception:
    VoicevoxEngine = None
    SynthParams = None

# ─────────────────────────────────────────────
#  COLOR PALETTE  (Dark Ink + Sakura accents)
# ─────────────────────────────────────────────
C = {
    "bg_dark":      "#0d0e14",
    "bg_panel":     "#13141f",
    "bg_card":      "#1a1b2e",
    "bg_hover":     "#21233a",
    "border":       "#2a2d47",
    "border_lit":   "#3d4270",

    "kotoba_bg":    "#1a2340",
    "kotoba_hdr":   "#1e3a7a",
    "kotoba_accent":"#4a90d9",
    "kotoba_glow":  "#2060b0",

    "grammar_bg":   "#2a1a35",
    "grammar_hdr":  "#5a1a7a",
    "grammar_accent":"#c060e8",
    "grammar_glow": "#8030c0",

    "group_bg":     "#1a2a1a",
    "group_hdr":    "#2a5a2a",
    "group_accent": "#60d960",

    "wire":         "#e8c060",
    "wire_sel":     "#ffd700",
    "wire_hover":   "#ffec80",

    "pin_idle":     "#444466",
    "pin_active":   "#88aaff",
    "pin_connected":"#60d9c0",

    "text_primary": "#e8eaf6",
    "text_secondary":"#8890b8",
    "text_kanji":   "#ffffff",
    "text_hira":    "#aabbdd",
    "text_accent":  "#c0d0ff",

    "sakura":       "#ff8fa3",
    "gold":         "#e8c060",
    "mint":         "#60d9c0",
    "red":          "#e85050",
    "green":        "#50c880",
}

FONT_JP   = QFont("Noto Sans JP, Yu Gothic, MS Gothic, sans-serif", 14)
FONT_KANJI = QFont("Noto Serif JP, Yu Mincho, serif", 18, QFont.Bold)
FONT_HIRA  = QFont("Noto Sans JP, Yu Gothic, sans-serif", 11)
FONT_LABEL = QFont("Helvetica Neue", 9)
FONT_TITLE = QFont("Helvetica Neue", 22, QFont.Bold)
FONT_MONO  = QFont("Consolas, Courier New, monospace", 10)

PIN_RADIUS = 7
BLOCK_W    = 160
KOTOBA_H   = 80
GRAMMAR_H  = 70
GROUP_H    = 60

PROJECTS_FILE  = Path.home() / ".kotoba_designer_projects.json"
STREAK_FILE    = Path.home() / ".kotoba_streak.json"
DICTIONARY_FILE= Path.home() / ".kotoba_dictionary.json"

APP_ROOT       = Path(__file__).resolve().parent
LESSON_DIR     = APP_ROOT / "data" / "lesson"
VOICE_DIR      = APP_ROOT / "voice"
SYSTEM_VOICE_DIR = VOICE_DIR / "system"

SYSTEM_AI_QUESTION_LINES = [
    "ねえねえ、ちょっと不思議な質問があるんだけど...",
    "ねえ、ちょっとミステリアスなこと聞いてもいい？",
    "ね、秘密の質問があるよ！",
    "ちょっと気になることあるんだけど、いいかな？",
]

RELATION_LABEL_POOL = [
    "りゆう", "けっか", "たいひ", "ほそく", "じゅんばん",
    "じかん", "ばしょ", "きっかけ", "れい", "まとまり",
]

_voice_engine = None
_voice_model_vvm = None


def lesson_slug(name: str) -> str:
    raw = (name or "lesson").strip().lower()
    raw = "".join(ch if ch.isalnum() else "_" for ch in raw)
    raw = "_".join(part for part in raw.split("_") if part)
    return raw or "lesson"


def ensure_lesson_dirs(lesson_name: str) -> tuple[Path, Path]:
    slug = lesson_slug(lesson_name)
    lesson_json_dir = LESSON_DIR
    lesson_voice_dir = VOICE_DIR / slug
    lesson_json_dir.mkdir(parents=True, exist_ok=True)
    lesson_voice_dir.mkdir(parents=True, exist_ok=True)
    return lesson_json_dir, lesson_voice_dir


def ensure_system_voice_dir() -> Path:
    SYSTEM_VOICE_DIR.mkdir(parents=True, exist_ok=True)
    return SYSTEM_VOICE_DIR


def export_lesson_json(project: "ProjectData") -> Path:
    lesson_json_dir, _ = ensure_lesson_dirs(project.name)
    out_file = lesson_json_dir / f"{lesson_slug(project.name)}.json"
    payload = {
        "id": project.id,
        "name": project.name,
        "created": project.created,
        "blocks": [b.to_dict() for b in project.blocks],
        "conns": [c.to_dict() for c in project.conns],
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    out_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), "utf-8")
    return out_file


def delete_lesson_artifacts(project_name: str):
    slug = lesson_slug(project_name)
    lesson_file = LESSON_DIR / f"{slug}.json"
    voice_dir = VOICE_DIR / slug
    try:
        if lesson_file.exists():
            lesson_file.unlink()
    except Exception:
        pass
    try:
        if voice_dir.exists():
            shutil.rmtree(voice_dir, ignore_errors=True)
    except Exception:
        pass


def get_voice_engine():
    global _voice_engine, _voice_model_vvm
    if _voice_engine is not None:
        return _voice_engine, _voice_model_vvm
    if VoicevoxEngine is None:
        return None, None
    try:
        _voice_engine = VoicevoxEngine(str(APP_ROOT / "voicevox"))
        models = _voice_engine.scan_models()
        if models:
            _voice_model_vvm = models[0]["vvm"]
    except Exception:
        _voice_engine = None
        _voice_model_vvm = None
    return _voice_engine, _voice_model_vvm


# ══════════════════════════════════════════════════════════════
#  DATA MODELS
# ══════════════════════════════════════════════════════════════

class BlockData:
    def __init__(self, btype="kotoba", x=0.0, y=0.0):
        self.id      = str(uuid.uuid4())[:8]
        self.btype   = btype          # "kotoba" | "grammar" | "group"
        self.kanji   = ""
        self.hira    = ""
        self.grammar = ""
        self.label   = ""
        self.x       = x
        self.y       = y

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items()}

    @classmethod
    def from_dict(cls, d):
        b = cls()
        b.__dict__.update(d)
        return b


class ConnectionData:
    def __init__(self, src_id="", dst_id="", src_pin="out", dst_pin="in", label=""):
        self.id      = str(uuid.uuid4())[:8]
        self.src_id  = src_id
        self.dst_id  = dst_id
        self.src_pin = src_pin   # "out_left" | "out_right" | etc.
        self.dst_pin = dst_pin
        self.label   = (label or random.choice(RELATION_LABEL_POOL))

    def to_dict(self):
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, d):
        c = cls()
        c.__dict__.update(d)
        return c


class ProjectData:
    def __init__(self, name="Untitled Lesson"):
        self.id      = str(uuid.uuid4())[:8]
        self.name    = name
        self.created = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.blocks  = []        # list of BlockData dicts
        self.conns   = []        # list of ConnectionData dicts

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "created": self.created,
            "blocks": [b.to_dict() for b in self.blocks],
            "conns":  [c.to_dict() for c in self.conns],
        }

    @classmethod
    def from_dict(cls, d):
        p = cls(d.get("name", "Lesson"))
        p.id      = d.get("id", p.id)
        p.created = d.get("created", p.created)
        p.blocks  = [BlockData.from_dict(b) for b in d.get("blocks", [])]
        p.conns   = [ConnectionData.from_dict(c) for c in d.get("conns", [])]
        return p


# ══════════════════════════════════════════════════════════════
#  GRAPHICS: PIN ITEM
# ══════════════════════════════════════════════════════════════

class PinItem(QGraphicsEllipseItem):
    def __init__(self, pin_id, parent_block):
        r = PIN_RADIUS
        super().__init__(-r, -r, r*2, r*2, parent_block)
        self.pin_id      = pin_id
        self.parent_block= parent_block
        self.connected   = False
        self._hovered    = False
        self._magneted   = False
        self.setAcceptHoverEvents(True)
        self.setZValue(10)
        self._refresh()

    def _refresh(self):
        if self._magneted:
            col = QColor(C["wire_sel"])
        elif self._hovered:
            col = QColor(C["pin_active"])
        elif self.connected:
            col = QColor(C["pin_connected"])
        else:
            col = QColor(C["pin_idle"])
        self.setBrush(QBrush(col))
        pen = QPen(col.lighter(150), 1.5)
        self.setPen(pen)

    def hoverEnterEvent(self, e):
        self._hovered = True
        self._refresh()
        self.setCursor(Qt.CrossCursor)
        super().hoverEnterEvent(e)

    def hoverLeaveEvent(self, e):
        self._hovered = False
        self._refresh()
        self.setCursor(Qt.ArrowCursor)
        super().hoverLeaveEvent(e)

    def scene_pos(self):
        return self.mapToScene(QPointF(0, 0))

    def set_connected(self, val):
        self.connected = val
        self._refresh()

    def set_magneted(self, val):
        self._magneted = val
        self._refresh()


# ══════════════════════════════════════════════════════════════
#  GRAPHICS: BASE BLOCK
# ══════════════════════════════════════════════════════════════

class BaseBlock(QGraphicsRectItem):
    """
    Abstract base – subclassed by KotobaBlock, GrammarBlock, GroupBlock
    Each block has:
      - a left input pin  (in)
      - a right output pin (out)
    """

    def __init__(self, data: BlockData, scene_ref):
        super().__init__(0, 0, BLOCK_W, self._height())
        self.data       = data
        self.scene_ref  = scene_ref
        self._selected_  = False
        self._hovered_   = False

        self.setPos(data.x, data.y)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)

        # Pins
        h = self._height()
        self.pin_in  = PinItem("in",  self)
        self.pin_out = PinItem("out", self)
        self.pin_in.setPos(0, h / 2)
        self.pin_out.setPos(BLOCK_W, h / 2)

        self._apply_shadow()
        self._draw()

    def _height(self):
        return KOTOBA_H

    def _apply_shadow(self):
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(3, 5)
        self.setGraphicsEffect(shadow)

    # ── colours (override in subclass) ──────────────────────
    def _col_bg(self):  return QColor(C["kotoba_bg"])
    def _col_hdr(self): return QColor(C["kotoba_hdr"])
    def _col_acc(self): return QColor(C["kotoba_accent"])

    def _draw(self):
        pass  # subclasses override paint()

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            self.data.x = self.x()
            self.data.y = self.y()
            if self.scene_ref:
                self.scene_ref.update_connections()
        return super().itemChange(change, value)

    def hoverEnterEvent(self, e):
        self._hovered_ = True
        self.update()
        super().hoverEnterEvent(e)

    def hoverLeaveEvent(self, e):
        self._hovered_ = False
        self.update()
        super().hoverLeaveEvent(e)

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.scene_ref.replay_voice.emit(self.data)
            e.accept()
            return
        super().mouseDoubleClickEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            # check if click is near a pin
            pos = e.pos()
            h = self._height()
            in_pos  = QPointF(0, h/2)
            out_pos = QPointF(BLOCK_W, h/2)
            if (pos - in_pos).manhattanLength() < PIN_RADIUS * 3:
                self.scene_ref.start_connection(self, "in")
                e.accept()
                return
            if (pos - out_pos).manhattanLength() < PIN_RADIUS * 3:
                self.scene_ref.start_connection(self, "out")
                e.accept()
                return
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        # Connection finishing is fully handled by NodeScene.mouseReleaseEvent
        super().mouseReleaseEvent(e)

    def contextMenuEvent(self, e):
        menu = QMenu()
        menu.setStyleSheet(_menu_style())
        edit_act  = menu.addAction("✏  Chỉnh sửa  /  Edit Block")
        voice_act = menu.addAction("🔊  Nghe lại  /  Replay Voice")
        menu.addSeparator()
        del_act   = menu.addAction("🗑  Xóa block  /  Delete")
        act = menu.exec(e.screenPos())
        if act == edit_act:
            self.scene_ref.open_edit_dialog(self)
        elif act == voice_act:
            self.scene_ref.replay_voice.emit(self.data)
        elif act == del_act:
            self.scene_ref.delete_block(self)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing)
        w = BLOCK_W
        h = self._height()
        r = 10

        bg  = self._col_bg()
        hdr = self._col_hdr()
        acc = self._col_acc()

        # selection / hover glow
        if self.isSelected():
            gp = QPen(acc, 2.5)
            painter.setPen(gp)
        elif self._hovered_:
            painter.setPen(QPen(acc.lighter(130), 1.5))
        else:
            painter.setPen(QPen(QColor(C["border"]), 1))

        # body
        body = QPainterPath()
        body.addRoundedRect(QRectF(0, 0, w, h), r, r)
        painter.fillPath(body, QBrush(bg))

        # header band
        hdr_h = 26
        hdr_path = QPainterPath()
        hdr_path.addRoundedRect(QRectF(0, 0, w, hdr_h), r, r)
        # clip top half only
        clip = QPainterPath()
        clip.addRect(QRectF(0, 0, w, hdr_h))
        painter.fillPath(hdr_path.intersected(clip), QBrush(hdr))

        # left accent stripe
        painter.fillRect(QRectF(0, 0, 4, h), QBrush(acc))

        # draw border on top
        painter.setPen(QPen(acc if self.isSelected() else QColor(C["border_lit"]), 1.2))
        painter.drawPath(body)

        self._paint_content(painter, w, h, hdr_h)

    def _paint_content(self, painter, w, h, hdr_h):
        pass


# ══════════════════════════════════════════════════════════════
#  KOTOBA BLOCK (Vocabulary)
# ══════════════════════════════════════════════════════════════

class KotobaBlock(BaseBlock):
    def _height(self): return KOTOBA_H
    def _col_bg(self):  return QColor(C["kotoba_bg"])
    def _col_hdr(self): return QColor(C["kotoba_hdr"])
    def _col_acc(self): return QColor(C["kotoba_accent"])

    def _paint_content(self, painter, w, h, hdr_h):
        # Header label
        painter.setPen(QColor(C["text_accent"]))
        f = QFont("Helvetica Neue", 7, QFont.Bold)
        f.setLetterSpacing(QFont.AbsoluteSpacing, 1.5)
        painter.setFont(f)
        painter.drawText(QRectF(8, 4, w-16, hdr_h-4), Qt.AlignVCenter, "言葉  KOTOBA")

        # Kanji
        kanji = self.data.kanji or "—"
        painter.setPen(QColor(C["text_kanji"]))
        fk = QFont("Yu Mincho, Noto Serif JP, serif", 20, QFont.Bold)
        painter.setFont(fk)
        painter.drawText(QRectF(8, hdr_h + 2, w - 16, 28),
                         Qt.AlignLeft | Qt.AlignVCenter, kanji)

        # Hiragana
        hira = self.data.hira or ""
        painter.setPen(QColor(C["text_hira"]))
        fh = QFont("Yu Gothic, Noto Sans JP, sans-serif", 10)
        painter.setFont(fh)
        painter.drawText(QRectF(8, hdr_h + 30, w - 16, 18),
                         Qt.AlignLeft | Qt.AlignVCenter, hira)

        # ID chip
        painter.setPen(QColor(C["text_secondary"]))
        fm = QFont("Consolas, monospace", 7)
        painter.setFont(fm)
        painter.drawText(QRectF(w - 38, h - 14, 36, 12),
                         Qt.AlignRight, f"#{self.data.id}")


# ══════════════════════════════════════════════════════════════
#  GRAMMAR BLOCK
# ══════════════════════════════════════════════════════════════

class GrammarBlock(BaseBlock):
    def _height(self): return GRAMMAR_H
    def _col_bg(self):  return QColor(C["grammar_bg"])
    def _col_hdr(self): return QColor(C["grammar_hdr"])
    def _col_acc(self): return QColor(C["grammar_accent"])

    def _paint_content(self, painter, w, h, hdr_h):
        # Header
        painter.setPen(QColor(C["grammar_accent"]))
        f = QFont("Helvetica Neue", 7, QFont.Bold)
        f.setLetterSpacing(QFont.AbsoluteSpacing, 1.5)
        painter.setFont(f)
        painter.drawText(QRectF(8, 4, w-16, hdr_h-4), Qt.AlignVCenter, "文法  GRAMMAR")

        # Grammar text
        txt = self.data.grammar or "—"
        painter.setPen(QColor("#e8aaff"))
        fg = QFont("Yu Gothic, Noto Sans JP, sans-serif", 14, QFont.Bold)
        painter.setFont(fg)
        painter.drawText(QRectF(8, hdr_h + 2, w - 16, h - hdr_h - 4),
                         Qt.AlignLeft | Qt.AlignVCenter, txt)

        painter.setPen(QColor(C["text_secondary"]))
        fm = QFont("Consolas, monospace", 7)
        painter.setFont(fm)
        painter.drawText(QRectF(w - 38, h - 14, 36, 12),
                         Qt.AlignRight, f"#{self.data.id}")


# ══════════════════════════════════════════════════════════════
#  GROUP BLOCK
# ══════════════════════════════════════════════════════════════

class GroupBlock(BaseBlock):
    def _height(self): return GROUP_H
    def _col_bg(self):  return QColor(C["group_bg"])
    def _col_hdr(self): return QColor(C["group_hdr"])
    def _col_acc(self): return QColor(C["group_accent"])

    def _paint_content(self, painter, w, h, hdr_h):
        painter.setPen(QColor(C["group_accent"]))
        f = QFont("Helvetica Neue", 7, QFont.Bold)
        f.setLetterSpacing(QFont.AbsoluteSpacing, 1.5)
        painter.setFont(f)
        painter.drawText(QRectF(8, 4, w-16, hdr_h-4), Qt.AlignVCenter, "グループ  GROUP")

        lbl = self.data.label or "Group"
        painter.setPen(QColor("#aaffaa"))
        fl = QFont("Helvetica Neue", 13, QFont.Bold)
        painter.setFont(fl)
        painter.drawText(QRectF(8, hdr_h + 2, w - 16, h - hdr_h - 4),
                         Qt.AlignLeft | Qt.AlignVCenter, lbl)


# ══════════════════════════════════════════════════════════════
#  CONNECTION WIRE (Bezier)
# ══════════════════════════════════════════════════════════════

class ConnectionItem(QGraphicsPathItem):
    def __init__(self, src_block, dst_block, conn_data, scene_ref):
        super().__init__()
        self.src_block = src_block
        self.dst_block = dst_block
        self.conn_data = conn_data
        self.scene_ref = scene_ref
        self._hovered  = False
        self.setZValue(1)
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self._update_path()

    def shape(self):
        """Wider hit area so wires are easy to click."""
        s = QPainterPathStroker()
        s.setWidth(14)
        return s.createStroke(self.path())

    def _update_path(self):
        src_pin = self.conn_data.src_pin if self.conn_data.src_pin in ("in", "out") else "out"
        dst_pin = self.conn_data.dst_pin if self.conn_data.dst_pin in ("in", "out") else "in"

        src_item = self.src_block.pin_in if src_pin == "in" else self.src_block.pin_out
        dst_item = self.dst_block.pin_in if dst_pin == "in" else self.dst_block.pin_out

        src = src_item.scene_pos()
        dst = dst_item.scene_pos()
        dx = abs(dst.x() - src.x())
        ctrl = max(dx * 0.5, 60)
        src_dir = -1 if src_pin == "in" else 1
        dst_dir = -1 if dst_pin == "in" else 1
        path = QPainterPath(src)
        path.cubicTo(
            QPointF(src.x() + ctrl * src_dir, src.y()),
            QPointF(dst.x() + ctrl * dst_dir, dst.y()),
            dst
        )
        self.setPath(path)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing)
        col = QColor(C["wire_sel"] if self.isSelected()
                     else C["wire_hover"] if self._hovered
                     else C["wire"])
        pen = QPen(col, 2.2, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(self.path())

        # Draw label badge at midpoint
        lbl = self.conn_data.label
        if lbl:
            mid = self.path().pointAtPercent(0.5)
            f = QFont("Helvetica Neue", 8, QFont.Bold)
            painter.setFont(f)
            fm = QFontMetrics(f)
            tw = fm.horizontalAdvance(lbl)
            th = fm.height()
            pad_x, pad_y = 6, 3
            bg = QRectF(mid.x() - tw/2 - pad_x,
                        mid.y() - th/2 - pad_y,
                        tw + pad_x*2, th + pad_y*2)
            painter.setBrush(QBrush(QColor(C["bg_panel"])))
            painter.setPen(QPen(col, 1))
            painter.drawRoundedRect(bg, 4, 4)
            painter.setPen(QColor(C["text_accent"]))
            painter.drawText(bg, Qt.AlignCenter, lbl)

    def hoverEnterEvent(self, e):
        self._hovered = True
        self.update()
        super().hoverEnterEvent(e)

    def hoverLeaveEvent(self, e):
        self._hovered = False
        self.update()
        super().hoverLeaveEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._edit_label()
            e.accept()
        else:
            super().mousePressEvent(e)

    def _edit_label(self):
        from PySide6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(
            None, "Tên kết nối  ·  Wire Label",
            "Đặt tên cho đường nối\n(ý nghĩa hoặc câu ghép):",
            text=self.conn_data.label
        )
        if ok:
            self.conn_data.label = text.strip()
            self.update()

    def contextMenuEvent(self, e):
        menu = QMenu()
        menu.setStyleSheet(_menu_style())
        edit_act   = menu.addAction("✏  Đặt tên  /  Edit Label")
        delete_act = menu.addAction("✂  Xóa dây  /  Delete Wire")
        act = menu.exec(e.screenPos())
        if act == edit_act:
            self._edit_label()
        elif act == delete_act:
            self.scene_ref.delete_connection(self)

    def refresh(self):
        self._update_path()


# ══════════════════════════════════════════════════════════════
#  TEMP WIRE (while dragging)
# ══════════════════════════════════════════════════════════════

class TempWire(QGraphicsPathItem):
    def __init__(self):
        super().__init__()
        self.setZValue(100)
        pen = QPen(QColor(C["wire"]), 2, Qt.DashLine, Qt.RoundCap)
        self.setPen(pen)

    def update_path(self, src: QPointF, dst: QPointF):
        dx = abs(dst.x() - src.x())
        ctrl = max(dx * 0.5, 60)
        path = QPainterPath(src)
        path.cubicTo(
            QPointF(src.x() + ctrl, src.y()),
            QPointF(dst.x() - ctrl, dst.y()),
            dst
        )
        self.setPath(path)


# ══════════════════════════════════════════════════════════════
#  NODE SCENE
# ══════════════════════════════════════════════════════════════

class NodeScene(QGraphicsScene):
    status_msg = Signal(str)
    block_created = Signal(object)
    block_updated = Signal(object)
    replay_voice  = Signal(object)

    def __init__(self, project: ProjectData):
        super().__init__()
        self.project     = project
        self._blocks: dict[str, BaseBlock] = {}
        self._conns:  list[ConnectionItem] = []
        self._connecting      = False
        self._conn_src_block  = None
        self._conn_src_pin    = None
        self._temp_wire       = None
        self._magnet_pin      = None
        self._magnet_threshold = 36.0
        self.setBackgroundBrush(QBrush(QColor(C["bg_dark"])))
        self._load_project()

    # ── load ────────────────────────────────────────────────
    def _load_project(self):
        self.clear()
        self._blocks.clear()
        self._conns.clear()
        for bd in self.project.blocks:
            self._add_block_from_data(bd)
        for cd in self.project.conns:
            src = self._blocks.get(cd.src_id)
            dst = self._blocks.get(cd.dst_id)
            if src and dst:
                wire = ConnectionItem(src, dst, cd, self)
                self.addItem(wire)
                self._conns.append(wire)
        self._refresh_pin_connections()

    def _pin_by_id(self, block: BaseBlock, pin_id: str) -> PinItem:
        return block.pin_in if pin_id == "in" else block.pin_out

    def _auto_connection_label(self, src_block: BaseBlock, dst_block: BaseBlock) -> str:
        """Return a sensible default relation label for a new connection."""
        sb = src_block.data.btype
        db = dst_block.data.btype
        if sb == "group" or db == "group":
            return random.choice(["まとまり", "テーマ", "ぶんるい"])
        if sb == "grammar" or db == "grammar":
            return random.choice(["パターン", "れい", "ほそく"])
        return random.choice(RELATION_LABEL_POOL)

    def _refresh_pin_connections(self):
        for blk in self._blocks.values():
            blk.pin_in.set_connected(False)
            blk.pin_out.set_connected(False)
        for wire in self._conns:
            src_pin = self._pin_by_id(wire.src_block, wire.conn_data.src_pin)
            dst_pin = self._pin_by_id(wire.dst_block, wire.conn_data.dst_pin)
            src_pin.set_connected(True)
            dst_pin.set_connected(True)

    def _add_block_from_data(self, data: BlockData) -> BaseBlock:
        if data.btype == "kotoba":
            blk = KotobaBlock(data, self)
        elif data.btype == "grammar":
            blk = GrammarBlock(data, self)
        else:
            blk = GroupBlock(data, self)
        self.addItem(blk)
        self._blocks[data.id] = blk
        return blk

    # ── public: add new block ───────────────────────────────
    def add_block(self, btype: str, pos: QPointF, **kwargs):
        data = BlockData(btype, pos.x(), pos.y())
        for k, v in kwargs.items():
            setattr(data, k, v)
        self.project.blocks.append(data)
        blk = self._add_block_from_data(data)
        self.block_created.emit(data)
        self.status_msg.emit(f"Created {btype} block  #{data.id}")
        return blk

    # ── connection logic ────────────────────────────────────
    def start_connection(self, block, pin_id):
        if self._connecting:
            self.cancel_connection()
        self._connecting     = True
        self._conn_src_block = block
        self._conn_src_pin   = pin_id
        self._set_magnet_pin(None)
        self._temp_wire = TempWire()
        self.addItem(self._temp_wire)
        self.status_msg.emit("Click target block to connect…  [Esc] to cancel")

    def _source_scene_pin_pos(self) -> QPointF:
        if not self._conn_src_block:
            return QPointF()
        if self._conn_src_pin == "in":
            return self._conn_src_block.pin_in.scene_pos()
        return self._conn_src_block.pin_out.scene_pos()

    def _candidate_target_pins(self):
        if not self._conn_src_block:
            return []
        pins = []
        for _, blk in self._blocks.items():
            if blk is self._conn_src_block:
                continue
            pins.append(blk.pin_in)
            pins.append(blk.pin_out)
        return pins

    def _nearest_target_pin(self, scene_pos: QPointF):
        nearest = None
        best = self._magnet_threshold
        for pin in self._candidate_target_pins():
            d = (pin.scene_pos() - scene_pos).manhattanLength()
            if d < best:
                best = d
                nearest = pin
        return nearest

    def _set_magnet_pin(self, pin: Optional[PinItem]):
        if self._magnet_pin is pin:
            return
        if self._magnet_pin:
            self._magnet_pin.set_magneted(False)
        self._magnet_pin = pin
        if self._magnet_pin:
            self._magnet_pin.set_magneted(True)

    def _find_target_pin(self, scene_pos):
        # 1. Pin hit-test under cursor (deterministic even when overlapping)
        direct_hits = []
        for item in self.items(scene_pos):
            if not isinstance(item, PinItem):
                continue
            if item.parent_block is self._conn_src_block:
                continue
            direct_hits.append(item)
        if direct_hits:
            return min(
                direct_hits,
                key=lambda p: (p.scene_pos() - scene_pos).manhattanLength(),
            )
        # 2. Magnet trong ngưỡng 36 px
        pin = self._nearest_target_pin(scene_pos)
        if pin:
            return pin
        # 3. Kéo thả vào bất kỳ điểm nào trên thân block → nối vào pin phù hợp
        blk = self._find_target_block(scene_pos)
        if blk:
            in_dist = (blk.pin_in.scene_pos() - scene_pos).manhattanLength()
            out_dist = (blk.pin_out.scene_pos() - scene_pos).manhattanLength()
            return blk.pin_in if in_dist <= out_dist else blk.pin_out
        return None

    def finish_connection(self, dst_block, dst_pin="in"):
        if not self._connecting:
            return
        src = self._conn_src_block
        if src is None or src is dst_block:
            self.cancel_connection()
            return

        src_block = src
        dst_block_final = dst_block
        src_pin = self._conn_src_pin if self._conn_src_pin in ("in", "out") else "out"
        dst_pin_final = dst_pin if dst_pin in ("in", "out") else "in"

        # avoid duplicate
        for c in self._conns:
            same_src = c.src_block is src_block and c.dst_block is dst_block_final
            same_pins = c.conn_data.src_pin == src_pin and c.conn_data.dst_pin == dst_pin_final
            if same_src and same_pins:
                self.cancel_connection()
                self.status_msg.emit("Already connected.")
                return

        label = self._auto_connection_label(src_block, dst_block_final)
        cd = ConnectionData(
            src_block.data.id,
            dst_block_final.data.id,
            src_pin,
            dst_pin_final,
            label=label,
        )
        self.project.conns.append(cd)

        wire = ConnectionItem(src_block, dst_block_final, cd, self)
        self.addItem(wire)
        self._conns.append(wire)
        self._refresh_pin_connections()

        self.cancel_connection()
        self.status_msg.emit(f"Connected #{src_block.data.id} → #{dst_block_final.data.id}")

    def cancel_connection(self):
        self._connecting = False
        self._conn_src_block = None
        self._conn_src_pin   = None
        self._set_magnet_pin(None)
        if self._temp_wire:
            self.removeItem(self._temp_wire)
            self._temp_wire = None

    def delete_connection(self, wire: ConnectionItem):
        if wire.conn_data in self.project.conns:
            self.project.conns.remove(wire.conn_data)
        self._conns.remove(wire)
        self.removeItem(wire)
        self._refresh_pin_connections()
        try:
            export_lesson_json(self.project)
        except Exception:
            pass

    def _remove_block_voice_file(self, block_data: BlockData):
        """Remove cached voice wav for a block if it exists."""
        # 1) Explicit stored path (if available)
        vf = getattr(block_data, "voice_file", "") or ""
        if vf:
            try:
                p = Path(vf)
                if p.exists() and p.is_file():
                    p.unlink()
            except Exception:
                pass

        # 2) Canonical path by lesson slug + block id
        try:
            _, lesson_voice_dir = ensure_lesson_dirs(self.project.name)
            p2 = lesson_voice_dir / f"{block_data.id}.wav"
            if p2.exists() and p2.is_file():
                p2.unlink()
        except Exception:
            pass

    def delete_block(self, block: BaseBlock):
        # remove wires
        to_remove = [c for c in self._conns
                     if c.src_block is block or c.dst_block is block]
        for w in to_remove:
            self.delete_connection(w)

        # remove associated audio cache file (if any)
        self._remove_block_voice_file(block.data)

        if block.data in self.project.blocks:
            self.project.blocks.remove(block.data)
        del self._blocks[block.data.id]
        self.removeItem(block)
        try:
            export_lesson_json(self.project)
        except Exception:
            pass

    def update_connections(self):
        for c in self._conns:
            c.refresh()

    # ── mouse ───────────────────────────────────────────────
    def mouseMoveEvent(self, e):
        if self._connecting and self._temp_wire and self._conn_src_block:
            src_pos = self._source_scene_pin_pos()
            magnet_pin = self._nearest_target_pin(e.scenePos())
            self._set_magnet_pin(magnet_pin)
            dst_pos = magnet_pin.scene_pos() if magnet_pin else e.scenePos()
            self._temp_wire.update_path(src_pos, dst_pos)
        super().mouseMoveEvent(e)

    def _find_target_block(self, scene_pos):
        """Return nearest block under scene_pos that is not the connection source."""
        candidates = []
        for item in self.items(scene_pos):
            blk = None
            if isinstance(item, PinItem):
                blk = item.parent_block
            elif isinstance(item, BaseBlock):
                blk = item
            if blk is None or blk is self._conn_src_block:
                continue
            if blk not in candidates:
                candidates.append(blk)
        if not candidates:
            return None
        return min(
            candidates,
            key=lambda b: (b.sceneBoundingRect().center() - scene_pos).manhattanLength(),
        )

    def mousePressEvent(self, e):
        if self._connecting:
            if e.button() == Qt.RightButton:
                self.cancel_connection()
                e.accept()
                return
            if e.button() == Qt.LeftButton:
                target_pin = self._find_target_pin(e.scenePos())
                if target_pin:
                    self.finish_connection(target_pin.parent_block, target_pin.pin_id)
                else:
                    # check if click on source block itself – stay in connecting mode
                    on_src = any(
                        isinstance(it, (BaseBlock, PinItem))
                        for it in self.items(e.scenePos())
                    )
                    if not on_src:
                        self.cancel_connection()
                e.accept()
                return
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        """Handles drag-to-connect: release over destination block."""
        if self._connecting and e.button() == Qt.LeftButton:
            target_pin = self._find_target_pin(e.scenePos())
            if target_pin:
                self.finish_connection(target_pin.parent_block, target_pin.pin_id)
                e.accept()
                return
        super().mouseReleaseEvent(e)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.cancel_connection()
        elif e.key() == Qt.Key_Delete:
            for item in self.selectedItems():
                if isinstance(item, BaseBlock):
                    self.delete_block(item)
                elif isinstance(item, ConnectionItem):
                    self.delete_connection(item)
        super().keyPressEvent(e)

    # ── edit dialog ─────────────────────────────────────────
    def open_edit_dialog(self, block: BaseBlock):
        dlg = BlockEditDialog(block.data)
        if dlg.exec():
            block.data.kanji   = dlg.f_kanji.text().strip()
            block.data.hira    = dlg.f_hira.text().strip()
            block.data.grammar = dlg.f_grammar.text().strip()
            block.data.label   = dlg.f_label.text().strip()
            block.update()
            self.block_updated.emit(block.data)
            self.status_msg.emit("Block updated.")

    # ── compile ─────────────────────────────────────────────
    def compile_sentence(self) -> str:
        """Traverse connections (DFS from root nodes) and build sentence."""
        # Find roots = blocks with no incoming wires
        has_incoming = {c.dst_block.data.id for c in self._conns}
        roots = [b for bid, b in self._blocks.items()
                 if bid not in has_incoming]

        visited = set()
        parts   = []

        def dfs(block):
            if block.data.id in visited:
                return
            visited.add(block.data.id)
            if block.data.btype == "kotoba":
                parts.append(block.data.kanji or block.data.hira)
            elif block.data.btype == "grammar":
                parts.append(block.data.grammar)
            else:
                parts.append(block.data.label)
            for wire in self._conns:
                if wire.src_block is block:
                    dfs(wire.dst_block)

        for r in roots:
            dfs(r)

        # fallback: all blocks not visited
        for bid, blk in self._blocks.items():
            if bid not in visited:
                if blk.data.btype == "kotoba":
                    parts.append(blk.data.kanji or blk.data.hira)
                elif blk.data.btype == "grammar":
                    parts.append(blk.data.grammar)
                else:
                    parts.append(blk.data.label)

        return "".join(parts)


# ══════════════════════════════════════════════════════════════
#  NODE VIEW
# ══════════════════════════════════════════════════════════════

class NodeView(QGraphicsView):
    def __init__(self, scene: NodeScene):
        super().__init__(scene)
        self.node_scene = scene
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.NoFrame)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setSceneRect(-5000, -5000, 10000, 10000)
        self.setStyleSheet(f"background:{C['bg_dark']};")
        self._pan_active = False
        self._pan_start  = None
        self._zoom_level = 1.0

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.node_scene.cancel_connection()
            e.accept()
            return
        if e.key() == Qt.Key_Delete:
            selected = list(self.node_scene.selectedItems())
            for item in selected:
                if isinstance(item, BaseBlock):
                    self.node_scene.delete_block(item)
                elif isinstance(item, ConnectionItem):
                    self.node_scene.delete_connection(item)
            if selected:
                self.node_scene.status_msg.emit("Deleted selected item(s).")
                e.accept()
                return
        super().keyPressEvent(e)

    def wheelEvent(self, e):
        factor = 1.15 if e.angleDelta().y() > 0 else 1 / 1.15
        new_zoom = self._zoom_level * factor
        if 0.15 < new_zoom < 5.0:
            self.scale(factor, factor)
            self._zoom_level = new_zoom

    def mousePressEvent(self, e):
        if e.button() == Qt.MiddleButton:
            self._pan_active = True
            self._pan_start  = e.position().toPoint()
            self.setCursor(Qt.ClosedHandCursor)
            e.accept()
            return
        if e.button() == Qt.RightButton and not self.node_scene._connecting:
            sp = self.mapToScene(e.position().toPoint())
            hit = self.node_scene.itemAt(sp, self.transform())
            if hit is None:
                self._show_context_menu(e.globalPosition().toPoint(), sp)
                return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._pan_active and self._pan_start:
            delta = e.position().toPoint() - self._pan_start
            self._pan_start = e.position().toPoint()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y())
            e.accept()
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MiddleButton:
            self._pan_active = False
            self.setCursor(Qt.ArrowCursor)
            e.accept()
            return
        super().mouseReleaseEvent(e)

    def _show_context_menu(self, global_pos, scene_pos):
        menu = QMenu(self)
        menu.setStyleSheet(_menu_style())
        menu.addSection("✦  Create Block")
        act_k = menu.addAction("🔵  言葉  Kotoba (Vocabulary)")
        act_g = menu.addAction("🟣  文法  Grammar")
        act_gr= menu.addAction("🟢  グループ  Group / Label")
        menu.addSeparator()
        act_fit = menu.addAction("⊡  Fit All to View")
        act_clr = menu.addAction("🗑  Clear All")

        act = menu.exec(global_pos)
        if act == act_k:
            dlg = QuickCreateDialog("kotoba")
            if dlg.exec():
                self.node_scene.add_block(
                    "kotoba", scene_pos,
                    kanji=dlg.f_kanji.text(),
                    hira=dlg.f_hira.text())
        elif act == act_g:
            dlg = QuickCreateDialog("grammar")
            if dlg.exec():
                self.node_scene.add_block(
                    "grammar", scene_pos,
                    grammar=dlg.f_grammar.text())
        elif act == act_gr:
            text, ok = QInputDialog.getText(
                self, "Group Name", "Label:", text="Group")
            if ok and text:
                self.node_scene.add_block("group", scene_pos, label=text)
        elif act == act_fit:
            self.fitInView(
                self.node_scene.itemsBoundingRect().adjusted(-40,-40,40,40),
                Qt.KeepAspectRatio)
        elif act == act_clr:
            r = QMessageBox.question(self, "Clear",
                "Remove all blocks?", QMessageBox.Yes | QMessageBox.No)
            if r == QMessageBox.Yes:
                ids = list(self.node_scene._blocks.keys())
                for bid in ids:
                    blk = self.node_scene._blocks.get(bid)
                    if blk:
                        self.node_scene.delete_block(blk)

    def zoom_reset(self):
        self.resetTransform()
        self._zoom_level = 1.0

    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)
        # Grid dots
        step = 40
        pen  = QPen(QColor(C["border"]), 1)
        painter.setPen(pen)
        left  = int(rect.left())  - int(rect.left())  % step
        top   = int(rect.top())   - int(rect.top())   % step
        x = left
        while x < rect.right():
            y = top
            while y < rect.bottom():
                painter.drawPoint(QPointF(x, y))
                y += step
            x += step


# ══════════════════════════════════════════════════════════════
#  DIALOGS
# ══════════════════════════════════════════════════════════════

def _dialog_style():
    return f"""
QDialog {{
    background: {C['bg_panel']};
    color: {C['text_primary']};
    border: 1px solid {C['border_lit']};
    border-radius: 12px;
}}
QLabel {{
    color: {C['text_secondary']};
    font-size: 11px;
}}
QLineEdit {{
    background: {C['bg_card']};
    color: {C['text_primary']};
    border: 1px solid {C['border']};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 14px;
}}
QLineEdit:focus {{
    border: 1px solid {C['kotoba_accent']};
}}
QPushButton {{
    background: {C['kotoba_hdr']};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 20px;
    font-size: 12px;
    font-weight: bold;
}}
QPushButton:hover {{ background: {C['kotoba_glow']}; }}
QPushButton#cancel {{
    background: {C['bg_card']};
    color: {C['text_secondary']};
    border: 1px solid {C['border']};
}}
"""


class QuickCreateDialog(QDialog):
    def __init__(self, btype):
        super().__init__()
        self.btype = btype
        self.setWindowTitle("Create Block")
        self.setStyleSheet(_dialog_style())
        self.setMinimumWidth(320)
        lay = QFormLayout(self)
        lay.setSpacing(10)
        lay.setContentsMargins(20, 20, 20, 20)

        if btype == "kotoba":
            self.f_kanji   = QLineEdit(); self.f_kanji.setPlaceholderText("漢字 Kanji")
            self.f_hira    = QLineEdit(); self.f_hira.setPlaceholderText("ひらがな Hiragana")
            self.f_grammar = QLineEdit()
            lay.addRow("漢字 :", self.f_kanji)
            lay.addRow("かな :", self.f_hira)
        else:
            self.f_kanji   = QLineEdit()
            self.f_hira    = QLineEdit()
            self.f_grammar = QLineEdit(); self.f_grammar.setPlaceholderText("〜ている、〜て...")
            lay.addRow("文法 :", self.f_grammar)

        btn_row = QHBoxLayout()
        ok_btn  = QPushButton("✓  Create")
        ok_btn.clicked.connect(self.accept)
        ca_btn  = QPushButton("Cancel"); ca_btn.setObjectName("cancel")
        ca_btn.clicked.connect(self.reject)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(ca_btn)
        lay.addRow(btn_row)


class BlockEditDialog(QDialog):
    def __init__(self, data: BlockData):
        super().__init__()
        self.setWindowTitle("Edit Block")
        self.setStyleSheet(_dialog_style())
        self.setMinimumWidth(340)
        lay = QFormLayout(self)
        lay.setSpacing(10)
        lay.setContentsMargins(20, 20, 20, 20)

        self.f_kanji   = QLineEdit(data.kanji)
        self.f_hira    = QLineEdit(data.hira)
        self.f_grammar = QLineEdit(data.grammar)
        self.f_label   = QLineEdit(data.label)

        if data.btype == "kotoba":
            lay.addRow("漢字 :", self.f_kanji)
            lay.addRow("かな :", self.f_hira)
        elif data.btype == "grammar":
            lay.addRow("文法 :", self.f_grammar)
        else:
            lay.addRow("Label :", self.f_label)

        btn_row = QHBoxLayout()
        ok = QPushButton("✓  Save"); ok.clicked.connect(self.accept)
        ca = QPushButton("Cancel"); ca.setObjectName("cancel"); ca.clicked.connect(self.reject)
        btn_row.addWidget(ok); btn_row.addWidget(ca)
        lay.addRow(btn_row)


def _menu_style():
    return f"""
QMenu {{
    background: {C['bg_panel']};
    color: {C['text_primary']};
    border: 1px solid {C['border_lit']};
    border-radius: 8px;
    padding: 4px;
    font-size: 12px;
}}
QMenu::item {{
    padding: 6px 20px 6px 10px;
    border-radius: 5px;
}}
QMenu::item:selected {{
    background: {C['bg_hover']};
    color: {C['text_accent']};
}}
QMenu::separator {{
    height: 1px;
    background: {C['border']};
    margin: 4px 8px;
}}
QMenu::section {{
    color: {C['text_secondary']};
    font-size: 10px;
    padding: 4px 10px;
}}
"""


# ══════════════════════════════════════════════════════════════
#  STREAK DATA  (daily activity streak + PentaPoints)
# ══════════════════════════════════════════════════════════════

class StreakData:
    def __init__(self):
        self.streak      = 0
        self.points      = 0
        self.last_active = ""
        self.energy      = 100
        self.energy_date = ""
        self.last_award  = None

    @classmethod
    def load(cls):
        s = cls()
        if STREAK_FILE.exists():
            try:
                d = json.loads(STREAK_FILE.read_text("utf-8"))
                s.streak      = d.get("streak", 0)
                s.points      = d.get("points", 0)
                s.last_active = d.get("last_active", "")
                s.energy      = d.get("energy", 100)
                s.energy_date = d.get("energy_date", "")
            except Exception:
                pass
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        if s.energy_date != today:
            s.energy = 100
            s.energy_date = today
        if s.last_active == today:
            pass                          # already active today
        elif s.last_active == yesterday:
            s.streak += 1
            s.last_active = today
            s.save()
        else:
            s.streak      = 1
            s.last_active = today
            s.save()
        return s

    def add_points(self, n: int, action: str = "generic") -> int:
        result = self.apply_reward(n, action)
        self.last_award = result
        return result["earned"]

    def apply_reward(self, base_points: int, action: str = "generic") -> dict:
        """
        Penta economy:
        - 100 energy per day (auto reset)
        - rewards become harder over time using logarithmic scaling
        - review can recover energy
        """
        today = datetime.now().strftime("%Y-%m-%d")
        if self.energy_date != today:
            self.energy = 100
            self.energy_date = today

        action_cost = {
            "new_lesson": 35,
            "dictionary_batch": 12,
            "review_complete": 18,
            "supplement": 25,
            "quiz_riddle": 16,
            "quiz_design": 24,
            "generic": 20,
        }
        cost = action_cost.get(action, action_cost["generic"])
        recovered = 0

        if self.energy < cost:
            if action == "review_complete":
                recovered = min(30, 100 - self.energy)
                self.energy += recovered
                self.save()
                return {
                    "earned": 0,
                    "cost": 0,
                    "energy": self.energy,
                    "recovered": recovered,
                    "reason": "review_recovery",
                }
            return {
                "earned": 0,
                "cost": 0,
                "energy": self.energy,
                "recovered": 0,
                "reason": "energy_empty",
            }

        self.energy -= cost
        difficulty = 1.0 + math.log1p(max(self.points, 0)) / 8.0
        earned = max(1, int(round(base_points / difficulty)))

        if action == "review_complete":
            recovered = min(20, 100 - self.energy)
            self.energy += recovered

        self.points += earned
        self.save()
        return {
            "earned": earned,
            "cost": cost,
            "energy": self.energy,
            "recovered": recovered,
            "reason": "ok",
        }
        self.save()

    def save(self):
        try:
            STREAK_FILE.write_text(
                json.dumps({"streak": self.streak,
                            "points": self.points,
                            "last_active": self.last_active,
                            "energy": self.energy,
                            "energy_date": self.energy_date},
                           ensure_ascii=False, indent=2),
                "utf-8"
            )
        except Exception:
            pass

    def penta_level(self) -> int:
        if self.streak <= 0:
            return 0
        return min(5, ((self.streak - 1) % 5) + 1)


_streak: Optional[StreakData] = None


def get_streak() -> StreakData:
    global _streak
    if _streak is None:
        _streak = StreakData.load()
    return _streak


# ══════════════════════════════════════════════════════════════
#  DICTIONARY DATA  (từ điển cá nhân  ·  3 từ = 1 PentaPoint)
# ══════════════════════════════════════════════════════════════

class DictionaryData:
    """
    Personal vocabulary dictionary.
    Every 3 words added earns 1 PentaPoint.
    """
    def __init__(self):
        self.words   : list[dict] = []   # {kanji, hira, meaning, added}
        self.pending : int        = 0    # words added since last point (0-2)

    @classmethod
    def load(cls):
        d = cls()
        if DICTIONARY_FILE.exists():
            try:
                raw = json.loads(DICTIONARY_FILE.read_text("utf-8"))
                d.words   = raw.get("words",   [])
                d.pending = raw.get("pending", 0)
            except Exception:
                pass
        return d

    def add_word(self, kanji: str, hira: str, meaning: str) -> int:
        """
        Add a word. Returns the number of PentaPoints just earned (0 or 1+).
        """
        kanji = (kanji or "").strip()
        hira = (hira or "").strip()
        meaning = " ".join((meaning or "").split())
        if not (kanji or hira):
            return 0

        today = datetime.now().strftime("%Y-%m-%d")

        # Upsert by (kanji, hira): avoid duplicate rows from repeated edits/adds.
        for w in self.words:
            if (w.get("kanji", "").strip() == kanji
                    and w.get("hira", "").strip() == hira):
                old_meaning = (w.get("meaning", "") or "").strip()
                if meaning:
                    if not old_meaning:
                        w["meaning"] = meaning
                    else:
                        parts = [p.strip() for p in old_meaning.split(";") if p.strip()]
                        if meaning not in parts:
                            w["meaning"] = old_meaning + "; " + meaning
                w["added"] = today
                self.save()
                return 0

        self.words.append({
            "kanji":   kanji,
            "hira":    hira,
            "meaning": meaning,
            "added":   today,
        })
        self.pending += 1
        earned = self.pending // 3
        self.pending  = self.pending % 3
        self.save()
        return earned

    def save(self):
        try:
            DICTIONARY_FILE.write_text(
                json.dumps({"words": self.words, "pending": self.pending},
                           ensure_ascii=False, indent=2),
                "utf-8"
            )
        except Exception:
            pass


_dictionary: Optional[DictionaryData] = None


def get_dictionary() -> DictionaryData:
    global _dictionary
    if _dictionary is None:
        _dictionary = DictionaryData.load()
    return _dictionary


# ══════════════════════════════════════════════════════════════
#  DICTIONARY DIALOG  (📝 Từ điển  ·  3 từ = +1 PentaPoint)
# ══════════════════════════════════════════════════════════════

class DictionaryDialog(QDialog):
    points_earned = Signal(int)   # emitted when words cross the 3-word threshold

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📝  Từ điển  ·  Personal Dictionary")
        self.setStyleSheet(_dialog_style())
        self.setMinimumSize(560, 540)
        self._dict = get_dictionary()
        self._build_ui()
        self._refresh_list()

    # ── UI ──────────────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(12)

        # ── Header ──────────────────────────────────────────
        hdr = QHBoxLayout()
        title = QLabel("📝  Từ điển cá nhân")
        title.setStyleSheet(
            f"color:{C['gold']};font-size:17px;font-weight:bold;")
        hdr.addWidget(title)
        hdr.addStretch()
        self.progress_lbl = QLabel()
        self.progress_lbl.setStyleSheet(
            f"color:{C['text_secondary']};font-size:11px;")
        hdr.addWidget(self.progress_lbl)
        root.addLayout(hdr)

        # ── Progress bar (next point) ────────────────────────
        prog_frame = QFrame()
        prog_frame.setStyleSheet(
            f"background:{C['bg_card']};border-radius:8px;border:1px solid {C['border']};")
        pflay = QHBoxLayout(prog_frame)
        pflay.setContentsMargins(12, 8, 12, 8)
        pflay.setSpacing(8)

        prog_icon = QLabel("⭐")
        pflay.addWidget(prog_icon)

        self.prog_dots = []
        for i in range(3):
            dot = QLabel("○")
            dot.setStyleSheet(f"font-size:18px;color:{C['border_lit']};")
            dot.setAlignment(Qt.AlignCenter)
            pflay.addWidget(dot)
            self.prog_dots.append(dot)

        pflay.addStretch()
        self.prog_hint = QLabel("3 từ = +1 PentaPoint")
        self.prog_hint.setStyleSheet(
            f"color:{C['text_secondary']};font-size:10px;font-style:italic;")
        pflay.addWidget(self.prog_hint)
        root.addWidget(prog_frame)

        # ── Word list ─────────────────────────────────────────
        self.word_list = QListWidget()
        self.word_list.setWordWrap(True)
        self.word_list.setStyleSheet(f"""
            QListWidget {{
                background:{C['bg_card']};
                border:1px solid {C['border']};
                border-radius:8px;
                padding:4px;
                color:{C['text_primary']};
                font-size:12px;
            }}
            QListWidget::item {{
                padding:6px 8px;
                border-radius:5px;
            }}
            QListWidget::item:selected {{
                background:{C['bg_hover']};
                color:{C['text_accent']};
            }}
            QScrollBar:vertical{{background:{C['bg_panel']};width:8px;border-radius:4px;}}
            QScrollBar::handle:vertical{{background:{C['border_lit']};border-radius:4px;}}
        """)
        root.addWidget(self.word_list, 1)

        # ── Add word form ──────────────────────────────────────
        add_frame = QFrame()
        add_frame.setStyleSheet(
            f"background:{C['bg_card']};border-radius:10px;border:1px solid {C['border_lit']};")
        flay = QGridLayout(add_frame)
        flay.setContentsMargins(14, 12, 14, 12)
        flay.setSpacing(8)

        def _field(ph):
            le = QLineEdit()
            le.setPlaceholderText(ph)
            le.setStyleSheet(
                f"background:{C['bg_panel']};color:{C['text_primary']};"
                f"border:1px solid {C['border']};border-radius:6px;"
                f"padding:6px 10px;font-size:13px;")
            return le

        self.f_kanji   = _field("漢字  (ví dụ: 食べる)")
        self.f_hira    = _field("ひらがな  (ví dụ: たべる)")
        self.f_meaning = _field("Nghĩa tiếng Việt (có thể nhiều từ, ví dụ: tổ tiên, ông bà)")

        flay.addWidget(QLabel("漢字"), 0, 0)
        flay.addWidget(self.f_kanji,   0, 1)
        flay.addWidget(QLabel("かな"),  0, 2)
        flay.addWidget(self.f_hira,    0, 3)
        flay.addWidget(QLabel("Nghĩa"),1, 0)
        flay.addWidget(self.f_meaning, 1, 1, 1, 3)

        for col in (0, 2):
            flay.itemAtPosition(0, col).widget().setStyleSheet(
                f"color:{C['text_secondary']};font-size:10px;")
        flay.itemAtPosition(1, 0).widget().setStyleSheet(
            f"color:{C['text_secondary']};font-size:10px;")

        add_btn = QPushButton("＋  Thêm từ")
        add_btn.setStyleSheet(
            f"QPushButton{{background:{C['group_hdr']};color:white;border:none;"
            f"border-radius:6px;padding:8px 18px;font-weight:bold;}}"
            f"QPushButton:hover{{background:{C['mint']};color:{C['bg_dark']};}}")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(self._add_word)
        flay.addWidget(add_btn, 2, 0, 1, 4, Qt.AlignRight)

        root.addWidget(add_frame)

        # ── Enter shortcut ──────────────────────────────────
        self.f_meaning.returnPressed.connect(self._add_word)

        # ── Close ────────────────────────────────────────────
        close_btn = QPushButton("Đóng")
        close_btn.setObjectName("cancel")
        close_btn.clicked.connect(self.accept)
        root.addWidget(close_btn, alignment=Qt.AlignRight)

    # ── Logic ────────────────────────────────────────────────
    def _add_word(self):
        kanji   = self.f_kanji.text().strip()
        hira    = self.f_hira.text().strip()
        meaning = self.f_meaning.text().strip()
        if not (kanji or hira):
            return
        earned = self._dict.add_word(kanji, hira, meaning)
        if earned:
            got = get_streak().add_points(earned, action="dictionary_batch")
            self.points_earned.emit(got)
        self.f_kanji.clear()
        self.f_hira.clear()
        self.f_meaning.clear()
        self.f_kanji.setFocus()
        self._refresh_list()

    def _refresh_list(self):
        self.word_list.clear()
        d = self._dict
        total = len(d.words)
        for w in reversed(d.words):
            kanji   = w.get("kanji", "")
            hira    = w.get("hira", "")
            meaning = w.get("meaning", "")
            added   = w.get("added", "")
            txt = f"  {kanji or hira}  ·  {hira if kanji else ''}  ·  {meaning}  ·  {added}"
            item = QListWidgetItem(txt)
            item.setToolTip(f"{kanji} | {hira} | {meaning} | {added}")
            self.word_list.addItem(item)

        # Update progress dots
        p = d.pending
        for i, dot in enumerate(self.prog_dots):
            if i < p:
                dot.setText("●")
                dot.setStyleSheet(f"font-size:18px;color:{C['gold']};")
            else:
                dot.setText("○")
                dot.setStyleSheet(f"font-size:18px;color:{C['border_lit']};")

        self.progress_lbl.setText(
            f"{total} từ  ·  {3 - p} từ nữa để đạt +1 điểm")


# ══════════════════════════════════════════════════════════════
#  REVIEW DIALOG  (📖 Ôn lại  ·  Flashcard  →  +1 PentaPoint)
# ══════════════════════════════════════════════════════════════

class ReviewDialog(QDialog):
    points_earned = Signal(int)

    def __init__(self, blocks: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📖  Ôn lại  ·  Flashcard Review")
        self.setStyleSheet(_dialog_style())
        self.setMinimumSize(500, 440)
        # Only kotoba/grammar blocks with content
        self._cards = [
            b for b in blocks
            if b.btype in ("kotoba", "grammar")
            and (b.kanji or b.hira or b.grammar)
        ]
        self._idx      = 0
        self._revealed = False
        self._done     = False
        self._build_ui()
        self._show_card()

    # ── UI ──────────────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        # Progress
        self.prog_lbl = QLabel()
        self.prog_lbl.setStyleSheet(
            f"color:{C['text_secondary']};font-size:11px;")
        self.prog_lbl.setAlignment(Qt.AlignCenter)
        root.addWidget(self.prog_lbl)

        # ── Flashcard ─────────────────────────────────────────
        self.card = QFrame()
        self.card.setMinimumHeight(220)
        self.card.setStyleSheet(
            f"background:{C['bg_card']};border-radius:16px;"
            f"border:2px solid {C['border_lit']};")
        clay = QVBoxLayout(self.card)
        clay.setContentsMargins(24, 24, 24, 24)
        clay.setAlignment(Qt.AlignCenter)

        self.type_lbl = QLabel()
        self.type_lbl.setAlignment(Qt.AlignCenter)
        self.type_lbl.setStyleSheet(
            f"color:{C['text_secondary']};font-size:10px;letter-spacing:2px;")
        clay.addWidget(self.type_lbl)

        self.front_lbl = QLabel()
        self.front_lbl.setAlignment(Qt.AlignCenter)
        self.front_lbl.setStyleSheet(
            f"color:white;font-size:40px;font-weight:bold;")
        self.front_lbl.setWordWrap(True)
        clay.addWidget(self.front_lbl)

        self.back_lbl = QLabel()
        self.back_lbl.setAlignment(Qt.AlignCenter)
        self.back_lbl.setStyleSheet(
            f"color:{C['text_hira']};font-size:18px;")
        self.back_lbl.setWordWrap(True)
        clay.addWidget(self.back_lbl)

        root.addWidget(self.card, 1)

        # ── Buttons ───────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self.reveal_btn = QPushButton("👁  Xem đáp án")
        self.reveal_btn.setStyleSheet(self._btn(C["kotoba_hdr"]))
        self.reveal_btn.setCursor(Qt.PointingHandCursor)
        self.reveal_btn.clicked.connect(self._reveal)
        btn_row.addWidget(self.reveal_btn)

        self.next_btn = QPushButton("→  Tiếp theo")
        self.next_btn.setStyleSheet(self._btn(C["grammar_hdr"]))
        self.next_btn.setCursor(Qt.PointingHandCursor)
        self.next_btn.clicked.connect(self._next)
        self.next_btn.setEnabled(False)
        btn_row.addWidget(self.next_btn)

        root.addLayout(btn_row)

        self.done_lbl = QLabel()
        self.done_lbl.setAlignment(Qt.AlignCenter)
        self.done_lbl.setStyleSheet(
            f"color:{C['gold']};font-size:14px;font-weight:bold;")
        self.done_lbl.hide()
        root.addWidget(self.done_lbl)

        close_btn = QPushButton("Đóng")
        close_btn.setObjectName("cancel")
        close_btn.clicked.connect(self.accept)
        root.addWidget(close_btn, alignment=Qt.AlignRight)

    def _btn(self, bg):
        return (f"QPushButton{{background:{bg};color:white;border:none;"
                f"border-radius:7px;padding:9px 20px;font-size:12px;font-weight:bold;}}"
                f"QPushButton:hover{{background:{C['border_lit']};color:{C['text_accent']};}}"
                f"QPushButton:disabled{{background:{C['bg_hover']};color:{C['text_secondary']};}}")

    # ── Logic ────────────────────────────────────────────────
    def _show_card(self):
        if not self._cards:
            self._finish(earned=False)
            return
        total = len(self._cards)
        idx   = self._idx
        b     = self._cards[idx]

        self.prog_lbl.setText(f"Thẻ {idx+1} / {total}")
        self._revealed = False
        self.next_btn.setEnabled(False)

        if b.btype == "kotoba":
            self.type_lbl.setText("言葉  KOTOBA")
            self.front_lbl.setText(b.kanji or b.hira)
            self.back_lbl.setText(b.hira if b.kanji else "")
            self.card.setStyleSheet(
                f"background:{C['kotoba_bg']};border-radius:16px;"
                f"border:2px solid {C['kotoba_accent']};")
        else:
            self.type_lbl.setText("文法  GRAMMAR")
            self.front_lbl.setText(b.grammar)
            self.back_lbl.setText("")
            self.card.setStyleSheet(
                f"background:{C['grammar_bg']};border-radius:16px;"
                f"border:2px solid {C['grammar_accent']};")

        self.back_lbl.hide()
        self.reveal_btn.setEnabled(True)
        self.reveal_btn.setText("👁  Xem đáp án")

    def _reveal(self):
        b = self._cards[self._idx]
        if b.btype == "kotoba":
            self.back_lbl.setText(b.hira if b.kanji else "(no reading)")
        else:
            self.back_lbl.setText("✓  Pattern grammar")
        self.back_lbl.show()
        self._revealed = True
        self.reveal_btn.setEnabled(False)
        self.next_btn.setEnabled(True)

    def _next(self):
        self._idx += 1
        if self._idx >= len(self._cards):
            self._finish(earned=True)
        else:
            self._show_card()

    def _finish(self, earned: bool):
        self._done = True
        self.reveal_btn.hide()
        self.next_btn.hide()
        if earned:
            got = get_streak().add_points(1, action="review_complete")
            self.points_earned.emit(got)
            self.done_lbl.setText(
                "🎉  Ôn lại hoàn tất!  phần thưởng đã được áp dụng ✦")
        else:
            self.done_lbl.setText("Không có block nào để ôn lại.")
        self.done_lbl.show()
        self.card.setStyleSheet(
            f"background:{C['group_bg']};border-radius:16px;"
            f"border:2px solid {C['group_accent']};")
        self.front_lbl.setText("✓")
        self.front_lbl.setStyleSheet(
            f"color:{C['green']};font-size:60px;font-weight:bold;")
        self.back_lbl.hide()
        self.type_lbl.setText("COMPLETE")


# ══════════════════════════════════════════════════════════════
#  PENTAPOINT DIALOG
# ══════════════════════════════════════════════════════════════

class PentaPointDialog(QDialog):
    def __init__(self, streak: StreakData, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PentaPoint")
        self.setStyleSheet(_dialog_style())
        self.setMinimumWidth(420)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(14)

        # Title
        ttl = QLabel("PentaPoint")
        ttl.setStyleSheet(f"color:{C['gold']};font-size:22px;font-weight:bold;")
        lay.addWidget(ttl)

        # Stats row
        stats_frame = QFrame()
        stats_frame.setStyleSheet(
            f"background:{C['bg_card']};border-radius:10px;border:1px solid {C['border_lit']};")
        sflay = QHBoxLayout(stats_frame)
        sflay.setContentsMargins(16, 12, 16, 12)

        def _stat(val, sub):
            w = QWidget()
            v = QVBoxLayout(w); v.setSpacing(2); v.setContentsMargins(0,0,0,0)
            lv = QLabel(f"{val}")
            lv.setStyleSheet(f"color:{C['text_primary']};font-size:20px;font-weight:bold;")
            ls = QLabel(sub)
            ls.setStyleSheet(f"color:{C['text_secondary']};font-size:10px;")
            v.addWidget(lv); v.addWidget(ls)
            return w

        sflay.addWidget(_stat(f"{streak.streak}", "ngày liên tục"))
        sep = QFrame(); sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet(f"color:{C['border']};")
        sflay.addWidget(sep)
        sflay.addWidget(_stat(f"{streak.points}", "PentaPoints"))
        sep2 = QFrame(); sep2.setFrameShape(QFrame.VLine)
        sep2.setStyleSheet(f"color:{C['border']};")
        sflay.addWidget(sep2)
        sflay.addWidget(_stat(f"{streak.energy}", "năng lượng hôm nay"))
        lay.addWidget(stats_frame)

        # Earn methods
        earn_lbl = QLabel("Cách kiếm điểm:")
        earn_lbl.setStyleSheet(
            f"color:{C['text_secondary']};font-size:11px;font-weight:bold;letter-spacing:1px;")
        lay.addWidget(earn_lbl)

        methods = [
            ("Tạo lesson mới",            "+2 điểm", C["kotoba_accent"]),
            ("Ôn lại bài tập lesson",      "+1 điểm", C["mint"]),
            ("Lesson bổ sung",             "+1 điểm", C["grammar_accent"]),
            ("3 từ trong từ điển",         "+1 điểm", C["gold"]),
            ("AI Câu đố",                  "điểm theo kết quả", C["wire_hover"]),
            ("AI Quiz",                    "điểm theo kết quả", C["sakura"]),
        ]
        for label, pts, col in methods:
            row_w = QFrame()
            row_w.setStyleSheet(
                f"background:{C['bg_card']};border-radius:6px;padding:2px;")
            rlay = QHBoxLayout(row_w)
            rlay.setContentsMargins(12, 6, 12, 6)
            l = QLabel(label)
            l.setStyleSheet(f"color:{C['text_primary']};font-size:12px;")
            r = QLabel(pts)
            r.setStyleSheet(f"color:{col};font-size:12px;font-weight:bold;")
            rlay.addWidget(l); rlay.addStretch(); rlay.addWidget(r)
            lay.addWidget(row_w)

        # Coming soon
        coming = QLabel("Tính năng đổi điểm đang được phát triển…")
        coming.setStyleSheet(
            f"color:{C['text_secondary']};font-size:10px;font-style:italic;")
        coming.setAlignment(Qt.AlignCenter)
        lay.addWidget(coming)

        ok = QPushButton("OK"); ok.clicked.connect(self.accept)
        ok.setStyleSheet(
            f"QPushButton{{background:{C['gold']};color:{C['bg_dark']};"
            f"border:none;border-radius:6px;padding:8px 28px;font-weight:bold;}}"
            f"QPushButton:hover{{background:{C['wire_hover']};}}")
        lay.addWidget(ok, alignment=Qt.AlignRight)


# ══════════════════════════════════════════════════════════════
#  STREAK PENTAGON WIDGET  (Dashboard toolbar)
# ══════════════════════════════════════════════════════════════

class StreakPentagonWidget(QWidget):
    """Pentagon + streak counter next to New Lesson button."""
    clicked = Signal()
    SIZE = 44

    def __init__(self, streak: StreakData, parent=None):
        super().__init__(parent)
        self.streak = streak
        sz = self.SIZE + 4
        self.setFixedSize(sz, sz)
        self.setCursor(Qt.PointingHandCursor)
        self._hovered = False
        self._build_tooltip()

    def _build_tooltip(self):
        s = self.streak
        level = s.penta_level()
        self.setToolTip(
            f"🔥 {s.streak} ngày liên tục\n"
            f"⭐ {s.points} PentaPoints\n\n"
            f"⚡ {s.energy}/100 năng lượng hôm nay\n"
            f"⬠ Level sáng: {level}/5\n\n"
            "Cách kiếm điểm:\n"
            "  ＋ Tạo lesson mới  → +2 điểm\n"
            "  📖 Ôn lại bài tập  → +1 điểm\n"
            "  📚 Lesson bổ sung  → +1 điểm\n"
            "  📝 3 từ từ điển   → +1 điểm\n\n"
            "Click để xem PentaPoint ✦"
        )

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        sz   = self.SIZE
        cx = cy = sz // 2 + 2
        R  = sz // 2 - 3
        n  = 5
        ao = -math.pi / 2
        # Pink → purple ramp: cạnh số i thắp sáng khi streak đạt cấp tương ứng
        STREAK_RAMP = [
            "#ffb3d1",  # cấp 1 – hồng nhạt
            "#ff79b0",  # cấp 2 – hồng tươi
            "#d94fa8",  # cấp 3 – hồng đậm
            "#913fcf",  # cấp 4 – tím hồng
            "#5e21b0",  # cấp 5 – tím đậm
        ]
        level = self.streak.penta_level()

        if level >= 5:
            glow = QRadialGradient(cx, cy, R + 10)
            glow.setColorAt(0.0, QColor(160, 60, 220, 140))
            glow.setColorAt(1.0, QColor(120, 30, 180, 0))
            painter.setBrush(QBrush(glow))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(cx, cy), R + 10, R + 10)

        for i in range(n):
            a1 = ao + 2*math.pi*i/n
            a2 = ao + 2*math.pi*(i+1)/n
            col = QColor(STREAK_RAMP[i])
            if i >= level:
                col = col.darker(280)
                col.setAlpha(90)
            if self._hovered:
                col = col.lighter(120)
            painter.setBrush(QBrush(col))
            painter.setPen(QPen(QColor(C["bg_dark"]), 1.2))
            painter.drawPolygon(QPolygonF([
                QPointF(cx, cy),
                QPointF(cx + R*math.cos(a1), cy + R*math.sin(a1)),
                QPointF(cx + R*math.cos(a2), cy + R*math.sin(a2)),
            ]))

        # cạnh sáng dùng màu của cấp đó, cạnh mờ dùng border_lit
        pts = [QPointF(cx + R*math.cos(ao + 2*math.pi*i/n),
                       cy + R*math.sin(ao + 2*math.pi*i/n)) for i in range(n)]
        for i in range(n):
            if i < level:
                painter.setPen(QPen(QColor(STREAK_RAMP[i]), 2.2))
            else:
                painter.setPen(QPen(QColor(C["border_lit"]), 1.0))
            painter.drawLine(pts[i], pts[(i + 1) % n])

        painter.setPen(QColor("white"))
        f = QFont("Helvetica Neue", 10, QFont.Bold)
        painter.setFont(f)
        painter.drawText(QRectF(cx-R*0.7, cy-R*0.7, R*1.4, R*1.4),
                         Qt.AlignCenter, str(self.streak.streak))

    def enterEvent(self, e):
        self._build_tooltip()
        self._hovered = True;  self.update()
    def leaveEvent(self, e):
        self._hovered = False; self.update()
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit()


# ══════════════════════════════════════════════════════════════
#  PENTALANG FLOATING BUTTON  (AssistiveTouch style)
# ══════════════════════════════════════════════════════════════

class PentaLangButton(QWidget):
    """
    Draggable pentagon overlay – like iOS AssistiveTouch.
    Can be placed anywhere on the workspace, not locked to edges.
    Pentagon is drawn as 5 coloured triangles (PentaYuki motif).
    """
    clicked = Signal()
    menu_requested = Signal()
    SIZE = 56

    def __init__(self, parent):
        super().__init__(parent)
        w = self.SIZE + 44   # extra width for "PentaLang" text
        h = self.SIZE + 18
        self.setFixedSize(w, h)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self._drag_offset = None
        self._hovered     = False
        self._press_pos   = None
        self._dragging    = False
        self.show_notification = False  # ✓ Badge flag
        self.streak       = get_streak()
        # Start near bottom-right; parent resizeEvent can reposition
        self._place_default()
        self.raise_()
        self.setCursor(Qt.ArrowCursor)

    def _place_default(self):
        if self.parent():
            pw, ph = self.parent().width(), self.parent().height()
            self.move(pw - self.width() - 24, ph - self.height() - 50)

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        S  = self.SIZE
        cx = S // 2 + 2
        cy = S // 2
        R  = S // 2 - 4
        n  = 5
        ao = -math.pi / 2

        # Minimal mode: khi không hover thì mờ 80%
        painter.setOpacity(1.0 if self._hovered else 0.2)

        # AssistiveTouch = một màu hoa hồng duy nhất, mỗi cánh chỉ đậm/nhạt nhẹ để tạo chiều sâu
        ROSE_PETALS = ["#ffc2d4", "#ff9ab8", "#ff8fa3", "#f0709a", "#d94f82"]
        alpha = 235 if self._hovered else 200

        # Outer soft glow khi hover
        if self._hovered:
            glow = QRadialGradient(cx, cy, R + 9)
            glow.setColorAt(0.0, QColor(255, 100, 160, 50))
            glow.setColorAt(1.0, QColor(255, 100, 160, 0))
            painter.setBrush(QBrush(glow))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(cx, cy), R + 9, R + 9)

        # 5 cánh hồng
        for i in range(n):
            a1 = ao + 2*math.pi*i/n
            a2 = ao + 2*math.pi*(i+1)/n
            col = QColor(ROSE_PETALS[i])
            col.setAlpha(alpha)
            if self._hovered:
                col = col.lighter(115)
            painter.setBrush(QBrush(col))
            painter.setPen(QPen(QColor(180, 40, 80, 100), 1))
            painter.drawPolygon(QPolygonF([
                QPointF(cx, cy),
                QPointF(cx + R*math.cos(a1), cy + R*math.sin(a1)),
                QPointF(cx + R*math.cos(a2), cy + R*math.sin(a2)),
            ]))

        # Viền ngoài
        pts = [QPointF(cx + R*math.cos(ao + 2*math.pi*i/n),
                       cy + R*math.sin(ao + 2*math.pi*i/n)) for i in range(n)]
        outline_alpha = 200 if self._hovered else 100
        painter.setPen(QPen(QColor(255, 150, 180, outline_alpha), 1.5))
        painter.setBrush(Qt.NoBrush)
        painter.drawPolygon(QPolygonF(pts))

        # On hover, show streak info and label.
        painter.setPen(QColor(C["text_primary"] if self._hovered else C["text_secondary"]))
        f = QFont("Helvetica Neue", 8, QFont.Bold)
        painter.setFont(f)
        if self._hovered:
            painter.drawText(
                QRectF(S + 6, cy - 12, self.width() - S - 8, 14),
                Qt.AlignVCenter | Qt.AlignLeft, "PentaLang"
            )
            painter.setFont(QFont("Helvetica Neue", 7, QFont.Bold))
            painter.setPen(QColor(C["gold"]))
            painter.drawText(
                QRectF(S + 6, cy + 2, self.width() - S - 8, 12),
                Qt.AlignVCenter | Qt.AlignLeft,
                f"Streak {self.streak.streak}d"
            )

        # ✓ Red notification badge when AI quiz is pending
        if self.show_notification:
            badge_x = S + 38
            badge_y = 4
            badge_r = 8
            painter.setOpacity(1.0)
            painter.setBrush(QBrush(QColor(220, 53, 69)))  # Red
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(badge_x, badge_y), badge_r, badge_r)
            # Optional: Add white "1" text in badge
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Helvetica Neue", 6, QFont.Bold))
            painter.drawText(
                QRectF(badge_x - 3, badge_y - 3, 6, 6),
                Qt.AlignCenter, "•"
            )

    def enterEvent(self, e):
        self._hovered = True;  self.update()
    def leaveEvent(self, e):
        self._hovered = False; self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_offset = e.position().toPoint()
            self._press_pos = e.position().toPoint()
            self._dragging = False
            self.setCursor(Qt.ClosedHandCursor)
            e.accept()

    def mouseMoveEvent(self, e):
        if self._drag_offset is not None and self.parent():
            if self._press_pos is not None:
                if (e.position().toPoint() - self._press_pos).manhattanLength() > 6:
                    self._dragging = True
            new_pos = self.mapToParent(e.position().toPoint() - self._drag_offset)
            pw, ph = self.parent().width(), self.parent().height()
            new_pos.setX(max(0, min(new_pos.x(), pw - self.width())))
            new_pos.setY(max(0, min(new_pos.y(), ph - self.height())))
            self.move(new_pos)
            e.accept()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            was_dragging = self._dragging
            self._drag_offset = None
            self._press_pos = None
            self._dragging = False
            self.setCursor(Qt.ArrowCursor)
            if not was_dragging:
                self.clicked.emit()
            e.accept()

    def mouseDoubleClickEvent(self, e):
        """Double-click shows quick-action menu."""
        if e.button() == Qt.LeftButton:
            self.menu_requested.emit()
            e.accept()


class DictionaryChatDialog(QDialog):
    """Simple dictionary assistant chat powered by personal dictionary data."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tra từ điển · PentaLang Chat")
        self.setStyleSheet(_dialog_style())
        self.setMinimumSize(560, 440)
        self._dict = get_dictionary()
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(10)

        self.chat = QTextEdit()
        self.chat.setReadOnly(True)
        self.chat.setStyleSheet(
            f"background:{C['bg_card']};color:{C['text_primary']};"
            f"border:1px solid {C['border']};border-radius:8px;padding:10px;font-size:12px;")
        self.chat.setText(
            "PentaLang Dictionary Chat\n"
            "- Nhap tu khoa (kanji/hiragana/nghia) de tra nhanh trong tu dien ca nhan.\n"
            "- Vi du: taberu, 食べる, an\n"
        )
        lay.addWidget(self.chat, 1)

        row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Nhap tu can tra...")
        self.input.returnPressed.connect(self._query)
        row.addWidget(self.input, 1)

        ask = QPushButton("Tra")
        ask.clicked.connect(self._query)
        row.addWidget(ask)
        lay.addLayout(row)

        close_btn = QPushButton("Dong")
        close_btn.setObjectName("cancel")
        close_btn.clicked.connect(self.accept)
        lay.addWidget(close_btn, alignment=Qt.AlignRight)

    def _query(self):
        q = self.input.text().strip()
        if not q:
            return
        key = q.lower()
        matches = []
        for w in reversed(self._dict.words):
            kanji = (w.get("kanji") or "").strip()
            hira = (w.get("hira") or "").strip()
            meaning = (w.get("meaning") or "").strip()
            blob = f"{kanji} {hira} {meaning}".lower()
            if key in blob:
                matches.append((kanji, hira, meaning, w.get("added", "")))
            if len(matches) >= 5:
                break

        self.chat.append(f"\nBan: {q}")
        if matches:
            self.chat.append("PentaLang:")
            for kanji, hira, meaning, added in matches:
                show = kanji or hira or "(khong ro)"
                self.chat.append(f"- {show} | {hira} | {meaning} | {added}")
        else:
            self.chat.append(
                "PentaLang: Chua tim thay trong tu dien ca nhan.\n"
                "Goi y: mo muc Tu dien de them tu moi roi tra lai."
            )
        self.input.clear()


class BonsaiChatDialog(QDialog):
    """
    Modern Chat Interface for LLM Yuki (Bonsai-8B).
    Context-aware chatting about the current lesson nodes.
    """

    def __init__(self, project_data: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Yuki-chan Assist ⬠")
        self.setMinimumSize(500, 600)
        self.setStyleSheet(f"""
            QDialog {{ background: {C['bg_dark']}; border: 1px solid {C['border']}; border-radius: 12px; }}
            QLineEdit {{ background: {C['bg_card']}; color: {C['text_primary']}; border: 1px solid {C['border']}; 
                         border-radius: 18px; padding: 10px 16px; font-size: 13px; }}
            QScrollArea {{ border: none; background: transparent; }}
        """)
        
        self.project_data = project_data
        self.llm = BonsaiLLM() if BonsaiLLM else None
        self.messages = []
        
        # Initial system prompt with context
        if self.llm:
            ctx = self.llm.format_lesson_context(project_data)
            self.messages.append({"role": "system", "content": self.llm.get_yuki_system_prompt(ctx)})

        self._build_ui()
        
        # Greeting
        QTimer.singleShot(500, self._greet)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(15, 15, 15, 15)
        root.setSpacing(10)

        # Header
        hdr = QLabel("💬  Yuki Chat")
        hdr.setStyleSheet(f"color: {C['sakura']}; font-size: 18px; font-weight: bold;")
        root.addWidget(hdr)

        # Chat Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.chat_container = QWidget()
        self.chat_container.setStyleSheet("background: transparent;")
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.addStretch()
        self.scroll.setWidget(self.chat_container)
        root.addWidget(self.scroll, 1)

        # Input Area
        input_row = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Hỏi Yuki bất cứ điều gì về bài học...")
        self.input_field.returnPressed.connect(self._send)
        input_row.addWidget(self.input_field)

        self.send_btn = QPushButton("🌸")
        self.send_btn.setFixedSize(36, 36)
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.setStyleSheet(f"""
            QPushButton {{ background: {C['sakura']}; border-radius: 18px; color: {C['bg_dark']}; font-size: 16px; }}
            QPushButton:hover {{ background: {C['wire_hover']}; }}
        """)
        self.send_btn.clicked.connect(self._send)
        input_row.addWidget(self.send_btn)
        root.addLayout(input_row)

    def _add_bubble(self, text: str, is_user: bool = False):
        bubble_row = QHBoxLayout()
        bubble_row.setContentsMargins(0, 0, 0, 0)
        
        # Bubble Frame
        frame = QFrame()
        bg = C['kotoba_hdr'] if not is_user else C['bg_hover']
        frame.setStyleSheet(f"""
            QFrame {{ background: {bg}; border-radius: 14px; border: 1px solid {C['border_lit']}; padding: 10px; }}
        """)
        flay = QVBoxLayout(frame)
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"color: {C['text_primary']}; font-size: 13px; background: transparent; border: none;")
        flay.addWidget(lbl)
        
        if is_user:
            bubble_row.addStretch()
            bubble_row.addWidget(frame)
        else:
            bubble_row.addWidget(frame)
            bubble_row.addStretch()
            
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, frame if is_user else frame) # Simplification
        # Reset stretch correctly
        # Fix: insert into layout
        self.chat_layout.takeAt(self.chat_layout.count() - 1) # remove stretch
        self.chat_layout.addLayout(bubble_row)
        self.chat_layout.addStretch()
        
        # Scroll to bottom
        QTimer.singleShot(50, lambda: self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum()))

    def _greet(self):
        self._add_bubble("Chào anh ạ! ✨ Em là Yuki đây. Em đã xem qua bài học của anh rùi. Anh cần em giúp gì về các từ vựng hay ngữ pháp này không ạ? 🌸")

    def _send(self):
        text = self.input_field.text().strip()
        if not text: return
        self.input_field.clear()
        
        self._add_bubble(text, is_user=True)
        self.messages.append({"role": "user", "content": text})
        
        # LLM Call
        if not self.llm:
            self._add_bubble("Hic, LLM Bonsai chưa được kết nối nên em chưa trả lời anh được ạ... 💧")
            return
            
        # Background processing or just simple blocking for now (to avoid complexity in this step)
        response = self.llm.chat(self.messages)
        self._add_bubble(response)
        self.messages.append({"role": "assistant", "content": response})


class AIQuizDialog(QDialog):
    """
    AI Quiz Dialog — redesigned with cultural theme support.
 
    Hiển thị câu hỏi theo theme 文化/旅行/妖怪/アニメ với:
    - Category chip đổi màu theo theme
    - Progress dots
    - 2×2 answer button grid
    - Animated result feedback + hint
    - Beautiful finish screen
    """
    points_earned = Signal(int)
 
    # ── Theme palette theo category ───────────────────────────────────────────
    _THEMES = {
        "⛩ 文化":   {"bg": "#0e2320", "card": "#122b28", "accent": "#50c0a0",
                      "border": "#1e5a4a", "chip_bg": "#1a4a3a", "chip_fg": "#80e8c8"},
        "🌸 旅行":   {"bg": "#1e0e22", "card": "#261228", "accent": "#e070b8",
                      "border": "#5a1a5a", "chip_bg": "#3a1040", "chip_fg": "#f0a0e0"},
        "👺 妖怪":   {"bg": "#0e0e24", "card": "#121230", "accent": "#9070e8",
                      "border": "#2a1a6a", "chip_bg": "#1c1048", "chip_fg": "#c0a8ff"},
        "🎌 アニメ": {"bg": "#220e0e", "card": "#2e1010", "accent": "#e87858",
                      "border": "#6a1a1a", "chip_bg": "#401414", "chip_fg": "#ffb08a"},
        "📖 読み方": {"bg": "#0e1622", "card": "#111c2e", "accent": "#6090d8",
                      "border": "#1a3a6a", "chip_bg": "#102040", "chip_fg": "#90c0ff"},
        "📝 文法":   {"bg": "#150e22", "card": "#1c1230", "accent": "#a070e0",
                      "border": "#3a1a6a", "chip_bg": "#241048", "chip_fg": "#d0a0ff"},
        "🔗 つながり": {"bg": "#0e1a14", "card": "#12221a", "accent": "#60d090",
                        "border": "#1a5030", "chip_bg": "#103820", "chip_fg": "#90ffb8"},
        "📚 グループ": {"bg": "#1a160e", "card": "#221e12", "accent": "#d0b050",
                        "border": "#5a4a10", "chip_bg": "#3a300a", "chip_fg": "#ffe080"},
        "🗂 設計":   {"bg": "#0e1820", "card": "#12202a", "accent": "#50a8c8",
                      "border": "#1a4060", "chip_bg": "#103050", "chip_fg": "#88d8f8"},
    }
    _DEFAULT_THEME = {
        "bg": "#0d0e14", "card": "#13141f", "accent": "#4a90d9",
        "border": "#2a2d47", "chip_bg": "#1e3a7a", "chip_fg": "#90c0ff",
    }
 
    def __init__(self, title: str, questions: list[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(700, 540)
        self.questions  = questions or []
        self.idx        = 0
        self.score      = 0
        self._answered  = False
        self._results   = []   # list of {"q": q, "correct": bool, "chosen": str}
        self._build_ui()
        if self.questions:
            self._render_question()
        else:
            self._show_empty()
 
    # ── Theme helpers ─────────────────────────────────────────────────────────
    def _theme(self, category: str = "") -> dict:
        return self._THEMES.get(category, self._DEFAULT_THEME)
 
    def _apply_theme(self, category: str):
        t = self._theme(category)
        # Dialog background
        self.setStyleSheet(f"""
            QDialog {{
                background: {t['bg']};
                border: 1px solid {t['border']};
                border-radius: 14px;
            }}
            QLabel {{
                background: transparent;
                color: {C['text_secondary']};
                font-size: 11px;
            }}
            QPushButton#cancel_btn {{
                background: {C['bg_card']};
                color: {C['text_secondary']};
                border: 1px solid {C['border']};
                border-radius: 6px;
                padding: 6px 18px;
                font-size: 11px;
            }}
            QPushButton#cancel_btn:hover {{
                background: {C['bg_hover']};
                color: {C['text_primary']};
            }}
        """)
        # Header
        self._header.setStyleSheet(
            f"background: {t['card']}; border-bottom: 1px solid {t['border']};"
        )
        # Category chip
        self._cat_chip.setStyleSheet(
            f"background: {t['chip_bg']}; color: {t['chip_fg']};"
            f"border: 1px solid {t['border']}; border-radius: 10px;"
            f"padding: 2px 10px; font-size: 11px; font-weight: bold;"
        )
        # Question card
        self._q_card.setStyleSheet(
            f"background: {t['card']}; border: 1px solid {t['border']};"
            f"border-radius: 14px;"
        )
        self._q_card_accent.setStyleSheet(
            f"background: {t['accent']}; border-radius: 3px;"
        )
        self._q_text.setStyleSheet(
            f"color: {C['text_primary']}; font-size: 16px; font-weight: bold;"
            f"background: transparent; border: none;"
        )
        # Answer buttons
        for btn in self._choice_btns:
            btn.setStyleSheet(self._btn_style_default(t))
            btn.setProperty("theme_accent", t["accent"])
            btn.setProperty("theme_border", t["border"])
        # Next btn
        self._next_btn.setStyleSheet(
            f"QPushButton {{ background: {t['accent']}; color: #0d0e14;"
            f" border: none; border-radius: 10px; font-size: 13px; font-weight: bold; }}"
            f"QPushButton:hover {{ background: {QColor(t['accent']).lighter(120).name()}; }}"
        )
        # Footer
        self._footer.setStyleSheet(
            f"background: {t['card']}; border-top: 1px solid {t['border']};"
        )
 
    def _btn_style_default(self, t: dict) -> str:
        return (
            f"QPushButton {{ background: {C['bg_card']}; color: {C['text_primary']};"
            f" border: 1px solid {C['border']}; border-radius: 10px;"
            f" padding: 10px 14px; text-align: left; font-size: 13px; }}"
            f"QPushButton:hover {{ border: 1px solid {t['accent']};"
            f" color: {t['chip_fg']}; background: {t['card']}; }}"
        )
 
    def _btn_style_correct(self) -> str:
        return (
            f"QPushButton {{ background: #103820; color: #80ffb0;"
            f" border: 2px solid #50c880; border-radius: 10px;"
            f" padding: 10px 14px; text-align: left; font-size: 13px;"
            f" font-weight: bold; }}"
        )
 
    def _btn_style_wrong(self) -> str:
        return (
            f"QPushButton {{ background: #2a0e0e; color: #ff8888;"
            f" border: 2px solid #e85050; border-radius: 10px;"
            f" padding: 10px 14px; text-align: left; font-size: 13px; }}"
        )
 
    def _btn_style_reveal_correct(self) -> str:
        return (
            f"QPushButton {{ background: #1a3820; color: #60d080;"
            f" border: 1px dashed #50c880; border-radius: 10px;"
            f" padding: 10px 14px; text-align: left; font-size: 13px; }}"
        )
 
    def _btn_style_disabled(self) -> str:
        return (
            f"QPushButton {{ background: {C['bg_card']}; color: {C['border_lit']};"
            f" border: 1px solid {C['border']}; border-radius: 10px;"
            f" padding: 10px 14px; text-align: left; font-size: 13px; }}"
        )
 
    # ── Build UI ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)
 
        # ── Header ─────────────────────────────────────────────────────────────
        self._header = QFrame()
        self._header.setFixedHeight(56)
        hlay = QHBoxLayout(self._header)
        hlay.setContentsMargins(20, 0, 20, 0)
        hlay.setSpacing(12)
 
        self._cat_chip = QLabel("─")
        hlay.addWidget(self._cat_chip)
        hlay.addStretch()
 
        # Progress dots
        self._dot_layout = QHBoxLayout()
        self._dot_layout.setSpacing(6)
        self._dot_layout.setContentsMargins(0, 0, 0, 0)
        self._dots: list[QLabel] = []
        n = len(self.questions)
        for _ in range(min(n, 10)):  # cap at 10 dots for space
            d = QLabel("○")
            d.setStyleSheet(f"color: {C['border_lit']}; font-size: 13px; background: transparent;")
            self._dot_layout.addWidget(d)
            self._dots.append(d)
        hlay.addLayout(self._dot_layout)
        hlay.addSpacing(14)
 
        # Score chip
        self._score_chip = QLabel("⭐  0")
        self._score_chip.setStyleSheet(
            f"color: {C['gold']}; font-size: 13px; font-weight: bold; background: transparent;"
        )
        hlay.addWidget(self._score_chip)
        main.addWidget(self._header)
 
        # ── Content ─────────────────────────────────────────────────────────────
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        clay = QVBoxLayout(content)
        clay.setContentsMargins(22, 18, 22, 14)
        clay.setSpacing(14)
 
        # Question card
        self._q_card = QFrame()
        self._q_card.setMinimumHeight(100)
        qlay = QVBoxLayout(self._q_card)
        qlay.setContentsMargins(18, 14, 18, 14)
        qlay.setSpacing(8)
 
        # Accent stripe (left side visual indicator)
        accent_row = QHBoxLayout()
        accent_row.setSpacing(12)
        self._q_card_accent = QFrame()
        self._q_card_accent.setFixedWidth(4)
        self._q_card_accent.setMinimumHeight(40)
        accent_row.addWidget(self._q_card_accent)
 
        self._q_text = QLabel()
        self._q_text.setWordWrap(True)
        self._q_text.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        font_q = QFont("Noto Sans JP, Yu Gothic, sans-serif", 15)
        font_q.setWeight(QFont.DemiBold)
        self._q_text.setFont(font_q)
        accent_row.addWidget(self._q_text, 1)
        qlay.addLayout(accent_row)
        clay.addWidget(self._q_card)
 
        # 2×2 choice grid
        grid_w = QWidget()
        grid_w.setStyleSheet("background: transparent;")
        grid = QGridLayout(grid_w)
        grid.setSpacing(10)
        grid.setContentsMargins(0, 0, 0, 0)
        self._choice_btns: list[QPushButton] = []
        for i in range(4):
            btn = QPushButton()
            btn.setCursor(Qt.PointingHandCursor)
            btn.setMinimumHeight(54)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            btn.setWordWrap(True)
            btn.setProperty("idx", i)
            btn.clicked.connect(lambda _, b=btn: self._choose(b))
            grid.addWidget(btn, i // 2, i % 2)
            self._choice_btns.append(btn)
        clay.addWidget(grid_w)
 
        # Result row (emoji + text)
        self._result_frame = QFrame()
        self._result_frame.setFixedHeight(46)
        self._result_frame.setStyleSheet(
            f"background: {C['bg_card']}; border-radius: 10px;"
        )
        rlay = QHBoxLayout(self._result_frame)
        rlay.setContentsMargins(14, 6, 14, 6)
        rlay.setSpacing(10)
        self._result_emoji = QLabel("")
        self._result_emoji.setStyleSheet("font-size: 22px; background: transparent;")
        rlay.addWidget(self._result_emoji)
        self._result_text = QLabel("")
        self._result_text.setWordWrap(True)
        self._result_text.setStyleSheet(
            f"color: {C['text_primary']}; font-size: 12px; background: transparent;"
        )
        rlay.addWidget(self._result_text, 1)
        self._result_frame.hide()
        clay.addWidget(self._result_frame)
 
        # Next button
        self._next_btn = QPushButton("次へ  →")
        self._next_btn.setFixedHeight(42)
        self._next_btn.setCursor(Qt.PointingHandCursor)
        font_next = QFont("Helvetica Neue", 13)
        font_next.setBold(True)
        self._next_btn.setFont(font_next)
        self._next_btn.clicked.connect(self._next)
        self._next_btn.hide()
        clay.addWidget(self._next_btn, alignment=Qt.AlignRight)
 
        main.addWidget(content, 1)
 
        # ── Footer ─────────────────────────────────────────────────────────────
        self._footer = QFrame()
        self._footer.setFixedHeight(48)
        flay = QHBoxLayout(self._footer)
        flay.setContentsMargins(20, 0, 20, 0)
        flay.setSpacing(10)
        self._hint_lbl = QLabel("")
        self._hint_lbl.setStyleSheet(
            f"color: {C['text_secondary']}; font-size: 10px;"
            f" font-style: italic; background: transparent;"
        )
        self._hint_lbl.setWordWrap(True)
        flay.addWidget(self._hint_lbl, 1)
        close_btn = QPushButton("Đóng")
        close_btn.setObjectName("cancel_btn")
        close_btn.setFixedSize(80, 30)
        close_btn.clicked.connect(self.accept)
        flay.addWidget(close_btn)
        main.addWidget(self._footer)
 
        # Apply default theme
        self._apply_theme("")
 
    # ── Render question ───────────────────────────────────────────────────────
    def _render_question(self):
        if self.idx >= len(self.questions):
            self._finish()
            return
 
        q = self.questions[self.idx]
        self._answered = False
        category = q.get("category", "")
 
        # Apply theme
        self._apply_theme(category)
 
        # Category chip
        self._cat_chip.setText(category or "📖 クイズ")
 
        # Progress dots
        for i, dot in enumerate(self._dots):
            if i < self.idx:
                dot.setText("●")
                dot.setStyleSheet(f"color: {C['mint']}; font-size: 13px; background: transparent;")
            elif i == self.idx:
                dot.setText("◉")
                t = self._theme(category)
                dot.setStyleSheet(f"color: {t['accent']}; font-size: 13px; background: transparent;")
            else:
                dot.setText("○")
                dot.setStyleSheet(f"color: {C['border_lit']}; font-size: 13px; background: transparent;")
 
        # Score
        self._score_chip.setText(f"⭐  {self.score}")
 
        # Question text
        self._q_text.setText(q.get("question", ""))
 
        # Hint
        hint = q.get("hint", "")
        self._hint_lbl.setText(f"💡 {hint}" if hint else "")
 
        # Choices
        choices = (q.get("choices") or [])[:4]
        t = self._theme(category)
        for i, btn in enumerate(self._choice_btns):
            if i < len(choices):
                btn.show()
                btn.setText(f"{'ＡＢＣＤ'[i]}  {choices[i]}")
                btn.setProperty("choice_val", choices[i])
                btn.setEnabled(True)
                btn.setStyleSheet(self._btn_style_default(t))
            else:
                btn.hide()
 
        # Reset result area
        self._result_frame.hide()
        self._result_emoji.setText("")
        self._result_text.setText("")
        self._next_btn.hide()
 
    def _choose(self, btn: QPushButton):
        if self._answered:
            return
        self._answered = True
        q       = self.questions[self.idx]
        ans     = q.get("answer", "")
        chosen  = btn.property("choice_val") or ""
        correct = (chosen == ans)
        pts     = int(q.get("points", 1)) if correct else 0
        self.score += pts
        self._results.append({"q": q, "correct": correct, "chosen": chosen})
 
        # Update score chip
        self._score_chip.setText(f"⭐  {self.score}")
 
        # Style chosen button
        t = self._theme(q.get("category", ""))
        for b in self._choice_btns:
            b.setEnabled(False)
            cv = b.property("choice_val") or ""
            if cv == ans:
                b.setStyleSheet(self._btn_style_correct())
            elif b is btn and not correct:
                b.setStyleSheet(self._btn_style_wrong())
            else:
                b.setStyleSheet(self._btn_style_disabled())
 
        # Show result
        self._result_frame.show()
        if correct:
            self._result_emoji.setText("✅")
            self._result_text.setText(
                f"<b style='color:#60d080;'>正解！</b>  +{pts}点  — {cute_reward_line()}"
            )
            self._result_text.setStyleSheet(
                f"color: {C['green']}; font-size: 12px; background: transparent;"
            )
        else:
            self._result_emoji.setText("❌")
            hint = q.get("hint", "")
            self._result_text.setText(
                f"<b style='color:#e85050;'>不正解。</b>  正解: 「{ans}」"
                + (f"  — {hint}" if hint else "")
            )
            self._result_text.setStyleSheet(
                f"color: {C['red']}; font-size: 12px; background: transparent;"
            )
 
        # Update current dot to checkmark
        if self.idx < len(self._dots):
            dot = self._dots[self.idx]
            dot.setText("●" if correct else "×")
            color = C['green'] if correct else C['red']
            dot.setStyleSheet(f"color: {color}; font-size: 13px; background: transparent;")
 
        self._next_btn.show()
 
    def _next(self):
        self.idx += 1
        self._render_question()
 
    def _finish(self):
        self.points_earned.emit(self.score)
 
        # Count stats
        total   = len(self.questions)
        correct = sum(1 for r in self._results if r["correct"])
        pct     = int(correct / max(1, total) * 100)
 
        # Choose finish emoji and rank
        if pct >= 80:
            rank_emoji, rank_text, rank_color = "🏆", "素晴らしい！", C["gold"]
            rank = "S"
        elif pct >= 60:
            rank_emoji, rank_text, rank_color = "⭐", "よくできました！", C["mint"]
            rank = "A"
        elif pct >= 40:
            rank_emoji, rank_text, rank_color = "📚", "もう少し！", C["kotoba_accent"]
            rank = "B"
        else:
            rank_emoji, rank_text, rank_color = "💪", "頑張れ！復習しよう！", C["sakura"]
            rank = "C"
 
        # Reuse q_card as finish card
        self._q_card.setStyleSheet(
            f"background: {C['bg_card']}; border: 1px solid {C['gold']}; border-radius: 14px;"
        )
        self._q_card_accent.setStyleSheet(
            f"background: {C['gold']}; border-radius: 3px;"
        )
        self._q_text.setStyleSheet(
            f"color: {C['gold']}; font-size: 20px; font-weight: bold; background: transparent; border: none;"
        )
        self._q_text.setText(
            f"{rank_emoji}  クイズ完了！\n\n"
            f"正解: {correct}/{total}  ({pct}%)\n"
            f"獲得ポイント: {self.score}"
        )
 
        # Hide choices, result, next
        for btn in self._choice_btns:
            btn.hide()
        self._result_frame.hide()
        self._next_btn.hide()
 
        # Cat chip → rank
        self._cat_chip.setText(f"{rank_emoji} {rank_text}")
        self._cat_chip.setStyleSheet(
            f"background: #2a2000; color: {rank_color}; border: 1px solid {C['gold']};"
            f"border-radius: 10px; padding: 2px 10px; font-size: 11px; font-weight: bold;"
        )
 
        # Hint → reward
        self._hint_lbl.setText(cute_reward_line(rank))
        self._hint_lbl.setStyleSheet(
            f"color: {C['text_accent']}; font-size: 12px; font-style: italic;"
            f" background: transparent;"
        )
 
        # Mark all dots
        for i, dot in enumerate(self._dots):
            if i < len(self._results):
                is_ok = self._results[i]["correct"]
                dot.setText("●" if is_ok else "×")
                dot.setStyleSheet(
                    f"color: {C['green'] if is_ok else C['red']};"
                    f" font-size: 13px; background: transparent;"
                )
 
        self._score_chip.setText(f"⭐  {self.score}")
 
    def _show_empty(self):
        self._q_text.setText("データが不足しています。\nlessонを追加してから再試行してください。")
        for btn in self._choice_btns:
            btn.hide()
        self._hint_lbl.setText("lesson にブロックを追加して、もう一度試してください。")
    points_earned = Signal(int)

    def __init__(self, title: str, questions: list[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setStyleSheet(_dialog_style())
        self.setMinimumSize(620, 420)
        self.questions = questions or []
        self.idx = 0
        self.score = 0
        self._build_ui()
        self._render_question()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(10)

        self.progress = QLabel()
        self.progress.setStyleSheet(f"color:{C['text_secondary']};font-size:11px;")
        lay.addWidget(self.progress)

        self.q_text = QLabel()
        self.q_text.setWordWrap(True)
        self.q_text.setStyleSheet(
            f"color:{C['text_primary']};font-size:16px;font-weight:bold;"
            f"background:{C['bg_card']};border:1px solid {C['border_lit']};"
            f"border-radius:10px;padding:14px;")
        lay.addWidget(self.q_text)

        self.choice_buttons = []
        for _ in range(4):
            btn = QPushButton("-")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, b=btn: self._choose(b.text()))
            btn.setStyleSheet(
                f"QPushButton{{background:{C['bg_card']};color:{C['text_primary']};"
                f"border:1px solid {C['border']};border-radius:8px;padding:10px;text-align:left;}}"
                f"QPushButton:hover{{border:1px solid {C['gold']};color:{C['gold']};}}")
            self.choice_buttons.append(btn)
            lay.addWidget(btn)

        self.result_lbl = QLabel("")
        self.result_lbl.setStyleSheet(f"color:{C['mint']};font-size:12px;")
        lay.addWidget(self.result_lbl)

        close_btn = QPushButton("閉じる")
        close_btn.setObjectName("cancel")
        close_btn.clicked.connect(self.accept)
        lay.addWidget(close_btn, alignment=Qt.AlignRight)

    def _render_question(self):
        if self.idx >= len(self.questions):
            self._finish()
            return
        q = self.questions[self.idx]
        self.progress.setText(f"問題 {self.idx+1}/{len(self.questions)} · スコア: {self.score}")
        self.q_text.setText(q.get("question", ""))
        choices = q.get("choices", [])[:4]
        for i, btn in enumerate(self.choice_buttons):
            if i < len(choices):
                btn.show()
                btn.setText(choices[i])
            else:
                btn.hide()
        self.result_lbl.setText("")

    def _choose(self, choice: str):
        q = self.questions[self.idx]
        ans = q.get("answer", "")
        if choice == ans:
            self.score += int(q.get("points", 1))
            self.result_lbl.setStyleSheet(f"color:{C['green']};font-size:12px;")
            self.result_lbl.setText("正解！ポイント追加 ✨")
        else:
            self.result_lbl.setStyleSheet(f"color:{C['red']};font-size:12px;")
            self.result_lbl.setText(f"不正解。正解は: {ans}")
        QTimer.singleShot(550, self._next)

    def _next(self):
        self.idx += 1
        self._render_question()

    def _finish(self):
        self.points_earned.emit(self.score)
        self.q_text.setText(f"完了！AIクイズの合計スコア: {self.score}")
        for btn in self.choice_buttons:
            btn.hide()
        self.result_lbl.setStyleSheet(f"color:{C['gold']};font-size:13px;font-weight:bold;")
        self.result_lbl.setText("ご褒美: " + cute_reward_line())


# ══════════════════════════════════════════════════════════════
#  WORKSPACE PAGE
# ══════════════════════════════════════════════════════════════

class WorkspacePage(QWidget):
    go_dashboard = Signal()

    def __init__(self):
        super().__init__()
        self.project = None
        self.scene   = None
        self.view    = None
        self.ai_core = LessonAI() if LessonAI else None
        self._last_system_voice_idx = -1
        self.ai_notice_pending = False
        self.ai_notice_mode = "periodic"
        self.ai_notice_expire_timer = QTimer(self)
        self.ai_notice_expire_timer.setSingleShot(True)
        self.ai_notice_expire_timer.timeout.connect(self._expire_ai_question_notice)
        self._build_ui()

        # ── Floating PentaLang button ────────────────────────
        self.penta_btn = PentaLangButton(self)
        self.penta_btn.clicked.connect(self._open_dictionary_chat)
        self.penta_btn.menu_requested.connect(self._pentalang_menu)
        self.penta_btn.show()

        # AI riddle cycle: periodically offers a quick riddle from data/lesson.
        self.ai_cycle_timer = QTimer(self)
        self.ai_cycle_timer.setInterval(180000)
        self.ai_cycle_timer.timeout.connect(self._ai_cycle_riddle)
        self.ai_cycle_timer.start()
        
        # Notification badge for pending AI quiz (flag, not auto-start)
        self.ai_quiz_pending = False
        self._ensure_system_voice_assets()


    def resizeEvent(self, e):
        super().resizeEvent(e)
        # Keep button within bounds after resize
        if hasattr(self, 'penta_btn'):
            pw, ph = self.width(), self.height()
            x = min(self.penta_btn.x(), pw - self.penta_btn.width() - 4)
            y = min(self.penta_btn.y(), ph - self.penta_btn.height() - 4)
            self.penta_btn.move(max(0, x), max(0, y))
            self.penta_btn.raise_()

    def _pentalang_menu(self):
        """Quick-access menu triggered by double-clicking PentaLang button."""
        if not self.scene:
            return
        menu = QMenu(self)
        menu.setStyleSheet(_menu_style())
        menu.addSection("⬠  PentaLang")
        ak  = menu.addAction("🔵  ＋ Kotoba")
        ag  = menu.addAction("🟣  ＋ Grammar")
        agr = menu.addAction("🟢  ＋ Group")
        menu.addSeparator()
        ad  = menu.addAction("📝  辞書 (3 words = +1 ⭐)")
        ach = menu.addAction("💬  ユキとチャット (LLM)")
        adic = menu.addAction("📑  辞書チャット")
        ar  = menu.addAction("📖  復習  (+1 ⭐)")
        arid = menu.addAction("🧩  AI クイズ (復習)")
        aqz = menu.addAction("🎮  AI クイズ (設計後)")
        menu.addSeparator()
        ac  = menu.addAction("▶  コンパイル")
        act = menu.exec(self.penta_btn.mapToGlobal(
            self.penta_btn.rect().center()))
        if   act == ak:  self._add_kotoba()
        elif act == ag:  self._add_grammar()
        elif act == agr: self._add_group()
        elif act == ad:  self._open_dictionary()
        elif act == ach: self._open_yuki_chat()
        elif act == adic: self._open_dictionary_chat()
        elif act == ar:  self._open_review()
        elif act == arid: self._open_ai_riddle_game()
        elif act == aqz: self._open_ai_design_game()
        elif act == ac:  self._compile()

    def _open_yuki_chat(self):
        if not self.project: return
        # Prepare context data
        data = {
            "name": self.project.name,
            "blocks": [b.to_dict() for b in self.project.blocks],
            "conns": [c.to_dict() for c in self.project.conns],
        }
        dlg = BonsaiChatDialog(data, self)
        dlg.exec()

    def _open_dictionary_chat(self):
        dlg = DictionaryChatDialog(self)
        dlg.exec()

    def _build_ui(self):
        self.setStyleSheet(f"background:{C['bg_dark']}; color:{C['text_primary']};")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── top bar ──────────────────────────────────────────
        bar = QFrame()
        bar.setFixedHeight(52)
        bar.setStyleSheet(
            f"background:{C['bg_panel']}; border-bottom:1px solid {C['border']};")
        blay = QHBoxLayout(bar)
        blay.setContentsMargins(14, 0, 14, 0)
        blay.setSpacing(10)

        back_btn = QPushButton("◀  Projects")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setStyleSheet(self._btn_style(C["kotoba_glow"]))
        back_btn.clicked.connect(self.go_dashboard.emit)
        blay.addWidget(back_btn)

        blay.addSpacing(8)
        self.title_lbl = QLabel("Untitled")
        self.title_lbl.setStyleSheet(
            f"font-size:15px; font-weight:bold; color:{C['text_primary']};")
        blay.addWidget(self.title_lbl)

        blay.addStretch()

        # tool buttons
        for label, tip, slot in [
            ("＋ 言葉",  "Add vocabulary block",  self._add_kotoba),
            ("＋ 文法", "Add grammar block",     self._add_grammar),
            ("＋ グループ",   "Add group / label",     self._add_group),
        ]:
            btn = QPushButton(label)
            btn.setToolTip(tip)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(self._btn_style(C["bg_card"]))
            btn.clicked.connect(slot)
            blay.addWidget(btn)

        blay.addSpacing(4)

        dict_btn = QPushButton("📝  辞書")
        dict_btn.setToolTip("Add words to dictionary (3 words = +1 ⭐)")
        dict_btn.setCursor(Qt.PointingHandCursor)
        dict_btn.setStyleSheet(self._btn_style(C["group_hdr"]))
        dict_btn.clicked.connect(self._open_dictionary)
        blay.addWidget(dict_btn)

        review_btn = QPushButton("📖  復習")
        review_btn.setToolTip("Review lesson (+1 ⭐)")
        review_btn.setCursor(Qt.PointingHandCursor)
        review_btn.setStyleSheet(self._btn_style(C["grammar_glow"]))
        review_btn.clicked.connect(self._open_review)
        blay.addWidget(review_btn)

        ai_riddle_btn = QPushButton("🧩  AI Câu đố")
        ai_riddle_btn.setToolTip("Tro choi on tap tu vocab/grammar/link trong lesson")
        ai_riddle_btn.setCursor(Qt.PointingHandCursor)
        ai_riddle_btn.setStyleSheet(self._btn_style(C["kotoba_hdr"]))
        ai_riddle_btn.clicked.connect(self._open_ai_riddle_game)
        blay.addWidget(ai_riddle_btn)

        self.ai_question_btn = QPushButton("?")
        self.ai_question_btn.setToolTip("定期的なAIクイズが待機中です")
        self.ai_question_btn.setCursor(Qt.PointingHandCursor)
        self.ai_question_btn.setFixedSize(28, 28)
        self.ai_question_btn.setStyleSheet(
            f"QPushButton{{background:{C['red']};color:white;border:1px solid {C['border_lit']};"
            f"border-radius:14px;font-size:16px;font-weight:bold;}}"
            f"QPushButton:hover{{background:{C['kotoba_glow']};color:white;}}"
        )
        self.ai_question_btn.clicked.connect(self._open_ai_periodic_game)
        self.ai_question_btn.hide()
        blay.addWidget(self.ai_question_btn)

        ai_quiz_btn = QPushButton("🎮  AI Quiz")
        ai_quiz_btn.setToolTip("Tro choi hoi dap sau khi thiet ke lesson")
        ai_quiz_btn.setCursor(Qt.PointingHandCursor)
        ai_quiz_btn.setStyleSheet(self._btn_style(C["group_hdr"]))
        ai_quiz_btn.clicked.connect(self._open_ai_design_game)
        blay.addWidget(ai_quiz_btn)

        yuki_chat_btn = QPushButton("💬  Yuki Chat")
        yuki_chat_btn.setToolTip("Hỏi Yuki về bài học hiện tại (Bonsai LLM)")
        yuki_chat_btn.setCursor(Qt.PointingHandCursor)
        yuki_chat_btn.setStyleSheet(self._btn_style(C["sakura"]))
        yuki_chat_btn.clicked.connect(self._open_yuki_chat)
        blay.addWidget(yuki_chat_btn)

        dict_chat_btn = QPushButton("📑  辞書チャット")
        dict_chat_btn.setToolTip("Quick dictionary chat")
        dict_chat_btn.setCursor(Qt.PointingHandCursor)
        dict_chat_btn.setStyleSheet(self._btn_style(C["bg_card"]))
        dict_chat_btn.clicked.connect(self._open_dictionary_chat)
        blay.addWidget(dict_chat_btn)

        blay.addSpacing(4)

        compile_btn = QPushButton("▶  コンパイル")
        compile_btn.setStyleSheet(self._btn_style(C["grammar_glow"]))
        compile_btn.setCursor(Qt.PointingHandCursor)
        compile_btn.clicked.connect(self._compile)
        blay.addWidget(compile_btn)

        save_btn = QPushButton("💾  Save")
        save_btn.setStyleSheet(self._btn_style(C["group_hdr"]))
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.clicked.connect(self._save)
        blay.addWidget(save_btn)

        root.addWidget(bar)

        # ── scene area ───────────────────────────────────────
        self.view_container = QWidget()
        vlay = QVBoxLayout(self.view_container)
        vlay.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.view_container, 1)

        # ── status bar ───────────────────────────────────────
        self.status = QLabel("Ready — Right-click canvas to create blocks")
        self.status.setFixedHeight(28)
        self.status.setStyleSheet(
            f"background:{C['bg_panel']}; color:{C['text_secondary']};"
            f"font-size:11px; padding:0 14px;"
            f"border-top:1px solid {C['border']};")
        root.addWidget(self.status)

    def _btn_style(self, bg):
        return (f"QPushButton{{background:{bg};color:white;border:none;"
                f"border-radius:6px;padding:6px 14px;font-size:11px;font-weight:bold;}}"
                f"QPushButton:hover{{background:{C['border_lit']};color:{C['text_accent']};}} ")

    def load_project(self, project: ProjectData):
        self.project = project
        self.title_lbl.setText(project.name)

        # replace old view
        if self.view:
            self.view_container.layout().removeWidget(self.view)
            self.view.deleteLater()

        self.scene = NodeScene(project)
        self.scene.status_msg.connect(self.status.setText)
        self.scene.block_created.connect(self._on_block_created)
        self.scene.block_updated.connect(self._on_block_updated)
        self.scene.replay_voice.connect(self._replay_block_voice)
        self.view = NodeView(self.scene)
        self.view_container.layout().addWidget(self.view)
        export_lesson_json(project)

    # ── toolbar actions ─────────────────────────────────────
    def _center_pos(self):
        if self.view:
            return self.view.mapToScene(
                self.view.viewport().rect().center())
        return QPointF(0, 0)

    def _block_voice_text(self, b: BlockData) -> str:
        if b.btype == "kotoba":
            if b.kanji and b.hira:
                return f"{b.kanji}、{b.hira}"
            return b.kanji or b.hira
        if b.btype == "grammar":
            return b.grammar
        return b.label

    def _voice_path_for_block(self, b: BlockData) -> Optional[Path]:
        if not self.project:
            return None
        _, lesson_voice_dir = ensure_lesson_dirs(self.project.name)
        return lesson_voice_dir / f"{b.id}.wav"

    def _speak_and_store_block(self, b: BlockData):
        txt = (self._block_voice_text(b) or "").strip()
        if not txt:
            return
        eng, vvm = get_voice_engine()
        if not eng or not vvm:
            return
        try:
            wav = eng.get_audio(txt, vvm, SynthParams()) if SynthParams else eng.get_audio(txt, vvm)
            out_path = self._voice_path_for_block(b)
            if wav and out_path:
                out_path.write_bytes(wav)
                b.voice_file = str(out_path)
            eng.speak_stream(txt, vvm, SynthParams()) if SynthParams else eng.speak_stream(txt, vvm)
        except Exception:
            pass

    def _on_block_created(self, b: BlockData):
        self._speak_and_store_block(b)
        if self.project:
            export_lesson_json(self.project)

    def _on_block_updated(self, b: BlockData):
        self._speak_and_store_block(b)
        if self.project:
            export_lesson_json(self.project)

    def _replay_block_voice(self, b: BlockData):
        """Phát lại âm thanh block — dùng file wav đã lưu nếu có, fallback sang TTS."""
        import subprocess as _sp
        out_path = self._voice_path_for_block(b)
        if out_path and out_path.exists():
            try:
                if sys.platform == "darwin":
                    _sp.Popen(["afplay", str(out_path)])
                    return
                elif sys.platform == "win32":
                    import winsound
                    winsound.PlaySound(str(out_path),
                                       winsound.SND_FILENAME | winsound.SND_ASYNC)
                    return
            except Exception:
                pass
        txt = (self._block_voice_text(b) or "").strip()
        if not txt:
            return
        eng, vvm = get_voice_engine()
        if not eng or not vvm:
            return
        try:
            if SynthParams:
                eng.speak_stream(txt, vvm, SynthParams())
            else:
                eng.speak_stream(txt, vvm)
        except Exception:
            pass

    def _add_kotoba(self):
        dlg = QuickCreateDialog("kotoba")
        if dlg.exec():
            sp = self._center_pos()
            self.scene.add_block("kotoba", sp,
                                 kanji=dlg.f_kanji.text(),
                                 hira=dlg.f_hira.text())

    def _add_grammar(self):
        dlg = QuickCreateDialog("grammar")
        if dlg.exec():
            sp = self._center_pos()
            self.scene.add_block("grammar", sp,
                                 grammar=dlg.f_grammar.text())

    def _add_group(self):
        text, ok = QInputDialog.getText(
            self, "Group / Label", "Name:", text="Group")
        if ok and text.strip():
            sp = self._center_pos()
            self.scene.add_block("group", sp, label=text.strip())

    def _compile(self):
        if not self.scene:
            return
        sent = self.scene.compile_sentence()
        if not sent:
            QMessageBox.information(self, "Compile", "No blocks to compile.")
            return
        dlg = CompileResultDialog(sent, self)
        dlg.exec()

    def _save(self):
        if self.project is None:
            return
        export_lesson_json(self.project)
        save_all_projects(_projects_cache)
        self.status.setText("✓ Saved  " + datetime.now().strftime("%H:%M:%S"))
        ask = QMessageBox.question(
            self,
            "AI Quiz",
            "Lesson đã lưu xong. Mở AI Quiz sau thiết kế ngay bây giờ?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if ask == QMessageBox.Yes:
            self._open_ai_design_game()

    def _open_dictionary(self):
        dlg = DictionaryDialog(self)
        dlg.points_earned.connect(self._award_toast)
        dlg.exec()

    def _open_review(self):
        if not self.scene:
            return
        blocks = list(self.scene.project.blocks)
        if not blocks:
            QMessageBox.information(self, "Ôn lại", "Lesson này chưa có block nào.")
            return
        dlg = ReviewDialog(blocks, self)
        dlg.points_earned.connect(self._award_toast)
        dlg.exec()

    def _current_lesson_json(self) -> Optional[Path]:
        if not self.project:
            return None
        try:
            return export_lesson_json(self.project)
        except Exception:
            return None

    def _build_ai_questions(self, mode: str) -> list[dict]:
        if not self.ai_core:
            return []
        try:
            if mode == "periodic":
                return self.ai_core.generate_cycle_puzzle(LESSON_DIR, count=5)
            lesson_file = self._current_lesson_json()
            if not lesson_file:
                return []
            if mode == "riddle":
                return self.ai_core.generate_riddle_game(lesson_file, count=5)
            return self.ai_core.generate_design_quiz(lesson_file, count=6)
        except Exception:
            return []

    def _voice_reward(self, text: str):
        eng, vvm = get_voice_engine()
        if not eng or not vvm:
            return
        try:
            eng.speak_stream(text, vvm, SynthParams()) if SynthParams else eng.speak_stream(text, vvm)
        except Exception:
            pass

    def _system_voice_file(self, idx: int) -> Path:
        return ensure_system_voice_dir() / f"system_ai_q_{idx + 1}.wav"

    def _ensure_system_voice_assets(self):
        """Generate reusable system voice wav files under voice/system."""
        try:
            ensure_system_voice_dir()
        except Exception:
            return
        eng, vvm = get_voice_engine()
        if not eng or not vvm:
            return
        for i, line in enumerate(SYSTEM_AI_QUESTION_LINES):
            out_path = self._system_voice_file(i)
            if out_path.exists():
                continue
            try:
                wav = eng.get_audio(line, vvm, SynthParams()) if SynthParams else eng.get_audio(line, vvm)
                if wav:
                    out_path.write_bytes(wav)
            except Exception:
                continue

    def _play_wav_async(self, wav_path: Path) -> bool:
        import subprocess as _sp
        try:
            if sys.platform == "darwin":
                _sp.Popen(["afplay", str(wav_path)])
                return True
            if sys.platform == "win32":
                import winsound
                winsound.PlaySound(str(wav_path), winsound.SND_FILENAME | winsound.SND_ASYNC)
                return True
        except Exception:
            return False
        return False

    def _pick_system_voice_index(self) -> int:
        n = len(SYSTEM_AI_QUESTION_LINES)
        if n <= 1:
            return 0
        choices = [i for i in range(n) if i != self._last_system_voice_idx]
        return random.choice(choices)

    def _play_system_ai_question_voice(self):
        idx = self._pick_system_voice_index()
        self._last_system_voice_idx = idx
        line = SYSTEM_AI_QUESTION_LINES[idx]
        self._ensure_system_voice_assets()
        out_path = self._system_voice_file(idx)
        if out_path.exists() and self._play_wav_async(out_path):
            return
        eng, vvm = get_voice_engine()
        if not eng or not vvm:
            return
        try:
            eng.speak_stream(line, vvm, SynthParams()) if SynthParams else eng.speak_stream(line, vvm)
        except Exception:
            pass

    def _show_ai_question_notice(self):
        self.ai_notice_pending = True
        self.ai_notice_mode = "periodic"
        self.ai_quiz_pending = True
        self.penta_btn.show_notification = True
        self.penta_btn.update()
        self.ai_question_btn.show()
        self.status.setText("AI định kỳ đang chờ. Nhấn ? để ôn tổng hợp từ nhiều lesson.")

        # Keep notice for 5-10 minutes
        ttl_ms = random.randint(5 * 60 * 1000, 10 * 60 * 1000)
        self.ai_notice_expire_timer.start(ttl_ms)

    def _expire_ai_question_notice(self):
        if not self.ai_notice_pending:
            return
        self.ai_notice_pending = False
        self.ai_quiz_pending = False
        self.penta_btn.show_notification = False
        self.penta_btn.update()
        self.ai_question_btn.hide()
        self.status.setText("Thông báo câu đố AI đã hết hạn.")

    def _run_ai_game(self, mode: str):
        if mode == "periodic":
            mode_title = "AI định kỳ nhắc lại"
        elif mode == "riddle":
            mode_title = "AI Câu đố ôn tập"
        else:
            mode_title = "AI Quiz sau thiết kế"
        qs = self._build_ai_questions(mode)
        if not qs:
            QMessageBox.information(self, mode_title, "Chưa đủ dữ liệu lesson để tạo câu hỏi AI.")
            return
        dlg = AIQuizDialog(mode_title, qs, self)

        def _on_finish(score: int):
            action = "quiz_design" if mode == "design" else "quiz_riddle"
            base = max(0, score // 2)
            earned = get_streak().add_points(base, action=action) if base > 0 else 0
            self._award_toast(earned)
            if score >= max(2, len(qs) // 2):
                reward = cute_reward_line()
                self._voice_reward(reward)

        dlg.points_earned.connect(_on_finish)
        dlg.exec()

    def _open_ai_riddle_game(self):
        self._run_ai_game("riddle")

    def _open_ai_design_game(self):
        self._run_ai_game("design")

    def _open_ai_periodic_game(self):
        self._clear_ai_notification()
        self._run_ai_game("periodic")

    def _clear_ai_notification(self):
        """Clear the AI quiz pending notification badge."""
        self.ai_notice_pending = False
        self.ai_quiz_pending = False
        if self.ai_notice_expire_timer.isActive():
            self.ai_notice_expire_timer.stop()
        self.penta_btn.show_notification = False
        self.penta_btn.update()
        self.ai_question_btn.hide()


    def _ai_cycle_riddle(self):
        if self.project is None or not self.isVisible() or self.scene is None:
            return
        
        if random.random() < 0.35:  # 35% chance to trigger
            self._show_ai_question_notice()
            self._play_system_ai_question_voice()


    def _award_toast(self, pts: int):
        """Flash a gold point-earned message in the status bar."""
        s = get_streak()
        last = s.last_award or {}
        if pts > 0:
            msg = (
                f"⭐ +{pts}  |  合計: {s.points}  |  ⚡ {s.energy}/100"
                f"  (コスト {last.get('cost', 0)})"
            )
        elif last.get("reason") == "review_recovery":
            msg = f"⚡ エネルギー回復 +{last.get('recovered', 0)}  |  {s.energy}/100"
        elif last.get("reason") == "energy_empty":
            msg = f"⚡ エネルギー不足 ({s.energy}/100). 復習して回復してください。"
        else:
            msg = f"⚡ {s.energy}/100 エネルギー"
        old_style = self.status.styleSheet()
        self.status.setStyleSheet(
            f"background:{C['kotoba_hdr']}; color:{C['gold']};"
            f"font-size:12px; font-weight:bold; padding:0 14px;"
            f"border-top:1px solid {C['gold']};")
        self.status.setText(msg)
        QTimer.singleShot(3500, lambda: (
            self.status.setStyleSheet(old_style),
            self.status.setText("準備完了 — 右クリックでブロックを作成できます")
        ))


# ══════════════════════════════════════════════════════════════
#  COMPILE RESULT DIALOG
# ══════════════════════════════════════════════════════════════

class CompileResultDialog(QDialog):
    def __init__(self, sentence, parent=None):
        super().__init__(parent)
        self.setWindowTitle("コンパイル結果")
        self.setMinimumWidth(480)
        self.setStyleSheet(_dialog_style())
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(12)

        lbl = QLabel("生成された日本語:")
        lbl.setStyleSheet(f"color:{C['text_secondary']}; font-size:11px;")
        lay.addWidget(lbl)

        txt = QLabel(sentence)
        txt.setStyleSheet(
            f"color:{C['text_kanji']}; font-size:28px; font-weight:bold;"
            f"background:{C['bg_card']}; border-radius:8px; padding:16px 20px;"
            f"border:1px solid {C['border_lit']};")
        txt.setWordWrap(True)
        txt.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(txt)

        ok = QPushButton("OK"); ok.clicked.connect(self.accept)
        ok.setStyleSheet(self._btn())
        lay.addWidget(ok, alignment=Qt.AlignRight)

    def _btn(self):
        return (f"QPushButton{{background:{C['kotoba_hdr']};color:white;"
                f"border:none;border-radius:6px;padding:8px 24px;font-weight:bold;}}")


# ══════════════════════════════════════════════════════════════
#  DASHBOARD
# ══════════════════════════════════════════════════════════════

class ProjectCard(QFrame):
    clicked = Signal(object)
    delete_requested = Signal(object)

    def __init__(self, project: ProjectData):
        super().__init__()
        self.project = project
        self.setFixedSize(220, 140)
        self.setCursor(Qt.PointingHandCursor)
        self._hovered = False
        self.setStyleSheet(self._style(False))

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(6)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)

        icon = QLabel("言")
        icon.setStyleSheet(
            f"color:{C['kotoba_accent']}; font-size:32px; font-weight:bold;")
        top_row.addWidget(icon)
        top_row.addStretch()

        del_btn = QPushButton("Delete")
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.setFixedHeight(22)
        del_btn.setStyleSheet(
            f"QPushButton{{background:{C['bg_panel']}; color:{C['text_secondary']};"
            f"border:1px solid {C['border']}; border-radius:6px; padding:0 8px; font-size:10px;}}"
            f"QPushButton:hover{{background:{C['red']}; color:white; border-color:{C['red']};}}"
        )
        del_btn.clicked.connect(lambda: self.delete_requested.emit(self.project))
        top_row.addWidget(del_btn)
        lay.addLayout(top_row)

        name = QLabel(project.name)
        name.setStyleSheet(
            f"color:{C['text_primary']}; font-size:13px; font-weight:bold;")
        name.setWordWrap(True)
        lay.addWidget(name)

        lay.addStretch()

        meta = QLabel(
            f"{len(project.blocks)} blocks · {project.created[:10]}")
        meta.setStyleSheet(
            f"color:{C['text_secondary']}; font-size:10px;")
        lay.addWidget(meta)

    def _style(self, hov):
        bg  = C["bg_hover"] if hov else C["bg_card"]
        brd = C["kotoba_accent"] if hov else C["border"]
        return (f"QFrame{{background:{bg};border:1px solid {brd};"
                f"border-radius:12px;}}")

    def enterEvent(self, e):
        self._hovered = True
        self.setStyleSheet(self._style(True))
    def leaveEvent(self, e):
        self._hovered = False
        self.setStyleSheet(self._style(False))
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit(self.project)

    def contextMenuEvent(self, e):
        menu = QMenu(self)
        menu.setStyleSheet(_menu_style())
        open_act = menu.addAction("Open Lesson")
        del_act = menu.addAction("Delete Lesson")
        act = menu.exec(e.globalPos())
        if act == open_act:
            self.clicked.emit(self.project)
        elif act == del_act:
            self.delete_requested.emit(self.project)


class DashboardPage(QWidget):
    open_project = Signal(object)

    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet(f"background:{C['bg_dark']}; color:{C['text_primary']};")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── hero header ──────────────────────────────────────
        hero = QFrame()
        hero.setFixedHeight(140)
        hero.setStyleSheet(
            f"background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            f"stop:0 {C['kotoba_hdr']}, stop:0.5 {C['grammar_hdr']}, stop:1 {C['bg_panel']});"
            f"border-bottom: 1px solid {C['border']};")
        hlay = QHBoxLayout(hero)
        hlay.setContentsMargins(48, 0, 48, 0)

        logo = QLabel("言葉デザイナー")
        logo.setStyleSheet(
            "font-size:36px; font-weight:bold; color:white; letter-spacing:2px;")
        hlay.addWidget(logo)

        hlay.addStretch()

        sub = QLabel("Kotoba Designer\nJapanese Language Node System")
        sub.setStyleSheet(
            f"font-size:13px; color:{C['text_hira']}; text-align:right;")
        sub.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        hlay.addWidget(sub)

        root.addWidget(hero)

        # ── toolbar row ──────────────────────────────────────
        tool_row = QFrame()
        tool_row.setFixedHeight(60)
        tool_row.setStyleSheet(
            f"background:{C['bg_panel']}; border-bottom:1px solid {C['border']};")
        tlay = QHBoxLayout(tool_row)
        tlay.setContentsMargins(40, 0, 40, 0)
        tlay.setSpacing(12)

        lbl = QLabel("Projects  /  レッスン一覧")
        lbl.setStyleSheet(
            f"font-size:13px; font-weight:bold; color:{C['text_secondary']};")
        tlay.addWidget(lbl)
        tlay.addStretch()

        new_btn = QPushButton("New Lesson")
        new_btn.setStyleSheet(
            f"QPushButton{{background:{C['kotoba_hdr']};color:white;"
            f"border:1px solid {C['border_lit']};border-radius:8px;padding:8px 22px;"
            f"font-size:12px;font-weight:bold;}}"
            f"QPushButton:hover{{background:{C['kotoba_glow']};border-color:{C['text_hira']};}}")
        new_btn.setCursor(Qt.PointingHandCursor)
        new_btn.clicked.connect(self._new_project)
        tlay.addWidget(new_btn)

        # Streak pentagon ────────────────────────────────────
        self.streak_widget = StreakPentagonWidget(get_streak())
        self.streak_widget.clicked.connect(self._open_penta_point)
        tlay.addWidget(self.streak_widget)

        root.addWidget(tool_row)

        # ── grid scroll area ─────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            f"QScrollArea{{background:{C['bg_dark']};border:none;}}"
            f"QScrollBar:vertical{{background:{C['bg_panel']};width:8px;border-radius:4px;}}"
            f"QScrollBar::handle:vertical{{background:{C['border_lit']};border-radius:4px;}}")
        inner = QWidget()
        inner.setStyleSheet(f"background:{C['bg_dark']};")
        self.grid = QGridLayout(inner)
        self.grid.setContentsMargins(40, 30, 40, 40)
        self.grid.setSpacing(20)
        self.grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        scroll.setWidget(inner)
        root.addWidget(scroll, 1)

        # ── bottom hint ──────────────────────────────────────
        hint = QLabel(
            "Double-click a block to edit  ·  Middle-click drag to pan  ·  "
            "Scroll to zoom  ·  Right-click canvas for menu  ·  Del to delete selected")
        hint.setFixedHeight(28)
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet(
            f"background:{C['bg_panel']};color:{C['text_secondary']};"
            f"font-size:10px;border-top:1px solid {C['border']};")
        root.addWidget(hint)

        self._refresh_cards()

    def _refresh_cards(self):
        # clear
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cols = 4
        for i, proj in enumerate(_projects_cache):
            card = ProjectCard(proj)
            card.clicked.connect(self.open_project.emit)
            card.delete_requested.connect(self._delete_project)
            self.grid.addWidget(card, i // cols, i % cols)

        if not _projects_cache:
            empty = QLabel("No lessons yet.\nClick  ＋ New Lesson  to begin.")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(
                f"color:{C['text_secondary']};font-size:14px;padding:60px;")
            self.grid.addWidget(empty, 0, 0)

    def _new_project(self):
        name, ok = QInputDialog.getText(
            self, "New Lesson", "Lesson name:", text="Lesson 1")
        if ok and name.strip():
            proj = ProjectData(name.strip())
            _projects_cache.append(proj)
            save_all_projects(_projects_cache)
            # Award points for creating a new lesson
            streak = get_streak()
            streak.add_points(2, action="new_lesson")
            self._refresh_cards()
            self.open_project.emit(proj)

    def _delete_project(self, proj: ProjectData):
        ask = QMessageBox.question(
            self,
            "レッスンの削除",
            f"レッスン '{proj.name}' を削除しますか？\nデータと音声ファイルがすべて消去されます。",
            QMessageBox.Yes | QMessageBox.No,
        )
        if ask != QMessageBox.Yes:
            return
        try:
            _projects_cache.remove(proj)
        except ValueError:
            return
        delete_lesson_artifacts(proj.name)
        save_all_projects(_projects_cache)
        self._refresh_cards()

    def _open_penta_point(self):
        dlg = PentaPointDialog(get_streak(), self)
        dlg.exec()


# ══════════════════════════════════════════════════════════════
#  PROJECT PERSISTENCE
# ══════════════════════════════════════════════════════════════

_projects_cache: list[ProjectData] = []


def load_projects() -> list[ProjectData]:
    if not PROJECTS_FILE.exists():
        return []
    try:
        data = json.loads(PROJECTS_FILE.read_text("utf-8"))
        return [ProjectData.from_dict(d) for d in data]
    except Exception:
        return []


def save_all_projects(projects: list[ProjectData]):
    try:
        PROJECTS_FILE.write_text(
            json.dumps([p.to_dict() for p in projects],
                       ensure_ascii=False, indent=2),
            "utf-8")
        for p in projects:
            try:
                export_lesson_json(p)
            except Exception:
                pass
    except Exception as ex:
        print("Save error:", ex)


# ══════════════════════════════════════════════════════════════
#  MAIN WINDOW
# ══════════════════════════════════════════════════════════════

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("言葉デザイナー  –  Kotoba Designer")
        self.resize(1440, 860)
        self.setMinimumSize(900, 600)

        # Stack
        self.stack    = QStackedWidget()
        self.dash     = DashboardPage()
        self.workspace= WorkspacePage()
        self.stack.addWidget(self.dash)
        self.stack.addWidget(self.workspace)
        self.setCentralWidget(self.stack)

        # Connections
        self.dash.open_project.connect(self._open_project)
        self.workspace.go_dashboard.connect(self._go_dashboard)

        # Global stylesheet
        self.setStyleSheet(f"""
            QMainWindow {{ background: {C['bg_dark']}; }}
            QToolTip {{
                background: {C['bg_panel']};
                color: {C['text_primary']};
                border: 1px solid {C['border_lit']};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }}
        """)

    def _open_project(self, proj: ProjectData):
        self.workspace.load_project(proj)
        self.stack.setCurrentWidget(self.workspace)

    def _go_dashboard(self):
        if self.workspace.project:
            save_all_projects(_projects_cache)
        self.dash._refresh_cards()
        self.stack.setCurrentWidget(self.dash)

    def closeEvent(self, e):
        save_all_projects(_projects_cache)
        super().closeEvent(e)


# ══════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════

def main():
    global _projects_cache
    app = QApplication(sys.argv)
    app.setApplicationName("Kotoba Designer")

    # Qt6 handles high-DPI pixmaps by default.

    _projects_cache = load_projects()
    if not _projects_cache:
        # seed demo project
        demo = ProjectData("Demo Lesson – 日本語")
        b1 = BlockData("kotoba", 80, 100);  b1.kanji="私"; b1.hira="わたし"
        b2 = BlockData("kotoba", 280, 100); b2.kanji="日本語"; b2.hira="にほんご"
        b3 = BlockData("grammar", 480, 100); b3.grammar="を話します"
        b4 = BlockData("kotoba", 180, 240); b4.kanji="勉強"; b4.hira="べんきょう"
        b5 = BlockData("grammar", 380, 240); b5.grammar="します"
        demo.blocks = [b1, b2, b3, b4, b5]
        c1 = ConnectionData(b1.id, b2.id)
        c2 = ConnectionData(b2.id, b3.id)
        c3 = ConnectionData(b4.id, b5.id)
        demo.conns = [c1, c2, c3]
        _projects_cache.append(demo)
        save_all_projects(_projects_cache)

    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
