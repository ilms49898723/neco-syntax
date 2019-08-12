#=============================================================================
# FILE: syntax.py
# AUTHOR:  Shougo Matsushita <Shougo.Matsu at gmail.com>
# License: MIT license
#=============================================================================

import string
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

        self.syntax_blacklist = set()
        for x in string.ascii_lowercase + string.hexdigits:
            self.syntax_blacklist.add('_{}'.format(x))
            self.syntax_blacklist.add('{}_'.format(x))
        for x in string.ascii_lowercase:
            self.syntax_blacklist.add('z{}'.format(x))
            for y in string.digits:
                self.syntax_blacklist.add('{}{}'.format(x, y))
        self.syntax_blacklist.add('__')
        self.syntax_blacklist.add('abfnrtv')

    def on_event(self, context: UserContext) -> None:
        syntax_candidates = [{'word': x} for x in
            self.vim.call('necosyntax#gather_candidates')
            if x.lower() not in self.syntax_blacklist and 'abfnrtv' not in x.lower()]
        syntax_candidates = sorted(syntax_candidates, key=lambda x: x['word'].swapcase())
        self.included_syntax[context['filetype']] = syntax_candidates

    def gather_candidates(self, context: UserContext) -> Candidates:
        return self.included_syntax.get(context['filetype'], [])
