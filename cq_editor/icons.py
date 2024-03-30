#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri May 25 14:47:10 2018

@author: adam
"""

from PyQt5.QtWidgets import QApplication, QPushButton
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QFont
from PyQt5.QtCore import QSize
from PyQt5.QtCore import Qt
from . import icons_res

_icons_specs = {
    'new'  : (('📄',),{}),
    'open' : (('📂',),{}),
    'autoreload': [('🔄', '⏰'), {'options': [{'scale_factor': 0.75, 'offset': (-0.1, -0.1)}, {'scale_factor': 0.5, 'offset': (0.25, 0.25)}]}],
    'save' : (('💾',),{}),
    'home_view': (('🧊','👁️'),
               {'options':[{'scale_factor': 1,},
                           {'scale_factor': 0.8,
                            'offset': (0.2, 0.2)}]}),
    'save_as': (('💾','⭐'),
               {'options':[{'scale_factor': 1,},
                           {'scale_factor': 0.8,
                            'offset': (0.2, 0.2)}]}),
    'debug' : (('🪲',),{}),
    'step_over' : (('➡️',),{}),
    'step_into' : (('⤵️',),{}),
    'continue' : (('⏩',),{}),
    'run'  : (('▶️',),{}),
    'delete' : (('🗑️',),{}),
    'delete-many' : (('🗑️','🗑️',),
                     {'options' : \
                      [{'scale_factor': 0.8,
                         'offset': (0.2, 0.2)},
                       {'scale_factor': 0.8}]}),
    'help' : (('❓',),{}),
    'about': (('📕',),{}),
    'preferences' : (('⚙️',),{}),
    'inspect' : (('🧊','🔎'),
                 {'options' : \
                  [{'scale_factor': 0.8,
                     'offset': (0,0)},{}]}),
    'screenshot' : (('📸',),{}),
    'docs' : (('📖',),{}),
    'screenshot-save' : (('💾','📸'),
                         {'options' : \
                          [{'scale_factor': 0.8},
                           {'scale_factor': 0.8,
                            'offset': (.2,.2)}]})
}

def icon(name, size=48):
    icons, settings = _icons_specs[name]

    pixmap = QPixmap(QSize(size, size))
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.TextAntialiasing, True)
    
    
    # Calculate the position to draw the emoji (center it)
    for idx, emoji in enumerate(icons):
        emojiOptions = settings.get('options', [{}])[idx]
        scaleFactor = emojiOptions.get('scale_factor', 1)
        offset = emojiOptions.get('offset', (0, 0))

        font = QFont("Segoe UI Emoji", round((size * 0.3) * scaleFactor))
        painter.setFont(font)

        fm = painter.fontMetrics()
        textWidth = fm.width(emoji)
        textHeight = fm.height()

        x = (size - textWidth) / 2 + int(offset[0] * size)
        y = (size - textHeight) / 2 + fm.ascent() + int(offset[1] * size)
        
        # Draw the emoji onto the pixmap
        painter.drawText(x, y, emoji)
    painter.end()
    
    # Convert the QPixmap into a QIcon and return
    return QIcon(pixmap)
    