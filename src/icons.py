"""矢量图标引擎：QPainter 绘制的线性图标（Lucide 风格），零 emoji、零外部资源。

用法：
    from PyQt6.QtWidgets import QPushButton
    btn.setIcon(icons.icon("plus", "#FFFFFF"))

所有图标在 24x24 逻辑网格上以描边绘制（圆头圆角），按 2x 设备像素渲染保证高分屏清晰。
"""
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap, QPolygonF

_CACHE = {}


def icon(name: str, color: str = "#5C6B84", size: int = 16, stroke: float = 1.7) -> QIcon:
    """生成线性图标。stroke 为 24 网格下的线宽。"""
    key = (name, color, size, stroke)
    if key in _CACHE:
        return _CACHE[key]

    dpr = 2
    pm = QPixmap(size * dpr, size * dpr)
    pm.fill(Qt.GlobalColor.transparent)

    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    s = pm.width() / 24.0
    p.scale(s, s)

    pen = QPen(QColor(color))
    pen.setWidthF(stroke)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)

    _draw(p, name, QColor(color))
    p.end()

    ic = QIcon(pm)
    _CACHE[key] = ic
    return ic


# ---------------------------------------------------------------- 24x24 绘制
def _poly(p: QPainter, pts):
    p.drawPolyline(QPolygonF([QPointF(x, y) for x, y in pts]))


def _draw(p: QPainter, name: str, col: QColor):
    if name == "plus":
        p.drawLine(QPointF(12, 5), QPointF(12, 19))
        p.drawLine(QPointF(5, 12), QPointF(19, 12))

    elif name == "minus":
        p.drawLine(QPointF(5, 12), QPointF(19, 12))

    elif name == "close":
        p.drawLine(QPointF(6.5, 6.5), QPointF(17.5, 17.5))
        p.drawLine(QPointF(17.5, 6.5), QPointF(6.5, 17.5))

    elif name == "square":  # 最大化
        p.drawRoundedRect(QRectF(6.5, 6.5, 11, 11), 2.5, 2.5)

    elif name == "restore":  # 还原（两层方框）
        p.drawRoundedRect(QRectF(5, 5, 9, 9), 2, 2)
        p.drawRoundedRect(QRectF(10, 10, 9, 9), 2, 2)

    elif name == "chevron-left":
        _poly(p, [(14.5, 6), (8.5, 12), (14.5, 18)])

    elif name == "chevron-right":
        _poly(p, [(9.5, 6), (15.5, 12), (9.5, 18)])

    elif name == "chevrons-left":  # 收起侧栏
        _poly(p, [(12.5, 6), (7, 12), (12.5, 18)])
        _poly(p, [(17.5, 6), (12, 12), (17.5, 18)])

    elif name == "chevrons-right":  # 展开侧栏
        _poly(p, [(11.5, 6), (17, 12), (11.5, 18)])
        _poly(p, [(6.5, 6), (12, 12), (6.5, 18)])

    elif name == "arrow-left":  # 后退
        p.drawLine(QPointF(19, 12), QPointF(5.5, 12))
        _poly(p, [(11, 6.5), (5.5, 12), (11, 17.5)])

    elif name == "arrow-right":  # 前进
        p.drawLine(QPointF(5, 12), QPointF(18.5, 12))
        _poly(p, [(13, 6.5), (18.5, 12), (13, 17.5)])

    elif name == "refresh":  # 顺时针刷新（圆弧 + 箭头）
        p.drawArc(QRectF(5.5, 5.5, 13, 13), 110 * 16, 300 * 16)
        p.drawLine(QPointF(19.5, 6.2), QPointF(16.4, 6.2))
        p.drawLine(QPointF(19.5, 6.2), QPointF(19.5, 9.5))

    elif name == "stop":  # 停止（小方框）
        p.drawRoundedRect(QRectF(7.5, 7.5, 9, 9), 2, 2)

    elif name == "external":  # 外部打开
        p.drawRoundedRect(QRectF(4.5, 9.5, 10, 10), 2.5, 2.5)
        p.drawLine(QPointF(11, 13), QPointF(19.5, 4.5))
        _poly(p, [(14.5, 4.5), (19.5, 4.5), (19.5, 9.5)])

    elif name == "sliders":  # 设置（滑杆）
        p.drawLine(QPointF(4, 6.5), QPointF(20, 6.5))
        p.drawLine(QPointF(4, 12), QPointF(20, 12))
        p.drawLine(QPointF(4, 17.5), QPointF(20, 17.5))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(col)
        p.drawEllipse(QPointF(15, 6.5), 2.4, 2.4)
        p.drawEllipse(QPointF(8.5, 12), 2.4, 2.4)
        p.drawEllipse(QPointF(16.5, 17.5), 2.4, 2.4)
        p.setBrush(Qt.BrushStyle.NoBrush)

    elif name == "search":  # 搜索
        p.drawEllipse(QPointF(10.8, 10.8), 5.3, 5.3)
        p.drawLine(QPointF(14.9, 14.9), QPointF(19.5, 19.5))

    elif name == "brand":  # 品牌环（白色圆环，叠在红底上）
        pen = QPen(col)
        pen.setWidthF(2.2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawEllipse(QPointF(12, 12), 5.4, 5.4)
        p.drawEllipse(QPointF(12, 12), 1.4, 1.4)

    else:  # 兜底：实心圆点
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(col)
        p.drawEllipse(QPointF(12, 12), 6, 6)
