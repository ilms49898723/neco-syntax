#=============================================================================
# FILE: syntax.py
# AUTHOR:  Shougo Matsushita <Shougo.Matsu at gmail.com>
# License: MIT license
#=============================================================================

import typing

from deoplete.base.source import Base
from deoplete.util import parse_buffer_pattern, getlines
from deoplete.util import Nvim, UserContext, Candidates


class Source(Base):
    def __init__(self, vim: Nvim) -> None:
        super().__init__(vim)

        self.name = 'syntax'
        self.mark = '[S]'
        self.events = None
        self.included_syntax = {}
        self.vim.call('necosyntax#initialize')

    def on_event(self, context: UserContext) -> None:
        self.included_syntax[context['filetype']] = [
            { 'word': x } for x in
            self.vim.call('necosyntax#gather_candidates')]

    def gather_candidates(self, context: UserContext) -> Candidates:
        return self.included_syntax.get(context['filetype'], [])
