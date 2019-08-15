#=============================================================================
# FILE: syntax.py
# AUTHOR:  Shougo Matsushita <Shougo.Matsu at gmail.com>
# License: MIT license
#=============================================================================

import queue
import re
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

    def parse_syntax(self, context):
        syntax_lines = self.vim.eval('execute("syntax list")')

        if re.match(r'^E\d+:', syntax_lines) or re.match(r'^No Syntax items', syntax_lines):
            return []

        keywords = []
        syntax_lines = syntax_lines.split('\n')
        for line in syntax_lines:
            line = self.parse_line(line)
            if line is None:
                continue

            matches = re.findall(r'[A-Za-z0-9_]\w*', line)
            for matched in matches:
                if len(matched) >= 2 and matched[0] not in string.digits:
                    keywords.append(matched)

        return list(set(keywords))

    def parse_line(self, line):
        if re.match(r'^\w*', line):
            line = re.sub(r'^\S+\s*', ' ', line, count=1)
            line = re.sub(r'^\s*xxx', ' ', line, count=1)

        if 'Syntax items' in line or re.match(r'^\s*links to', line) or re.match(r'^\s*cluster', line):
            return None

        line = line.replace('contained', ' ')
        line = line.replace('oneline', ' ')
        line = line.replace('skipwhite', ' ')
        line = line.replace('skipnl', ' ')

        line = re.sub(r'^\s*nextgroup=\S+', ' ', line)
        line = re.sub(r'contains=\S+', ' ', line)

        if re.match(r'^\s*match\s', line):
            line = self.parse_match(line)
        elif re.match(r'^\s*matchgroup=', line):
            line = self.parse_region(line)
        elif re.match(r'^\s*start=', line):
            line = self.parse_region(line)

        return line

    def parse_specials(self, line):
        line = re.sub(r"\\%[<>]?'.", ' ', line)
        line = re.sub(r"\\%[<>]?\d*.", ' ', line)
        line = re.sub(r"\\%[CV]", ' ', line)
        line = re.sub(r"\\%(d\d+|o[0-7]+|x[0-9A-Fa-f]{,2})", ' ', line)
        line = re.sub(r"\\%(u[0-9A-Fa-f]{,4}|U[0-9A-Fa-f]{,8})", ' ', line)
        line = re.sub(r"\\%#=\d", ' ', line)

        line = re.sub(r'\\_[$^.adfhiklopsuwxADFHIKLOPSUWX]', ' ', line)
        line = re.sub(r'\\(ze|zs|z[0-9])', ' ', line)

        line = re.sub(r'\[:.*:\]', ' ', line)

        line = line.replace('\\\\', ' ')
        line = re.sub(r'\\.', ' ', line)
        line = re.sub(r'\[.[^\]]*\]', ' ', line)

        return line

    def parse_pairs(self, line):
        line = line.replace('\\\\', ' ')

        line_queue = queue.Queue()
        line_queue.put_nowait(line)

        pair_patterns = [r'\\\((.*)\\\)', r'\\z\((.*)\\\)', r'\\%\((.*)\\\)']
        results = []
        while not line_queue.empty():
            top = line_queue.get_nowait()
            for pair_pattern in pair_patterns:
                matches = re.search(pair_pattern, top)
                if matches:
                    break
            else:
                results.append(top)
                continue

            patterns = matches.group(1).split('\|')
            for pattern in patterns:
                line_queue.put_nowait(top.replace(matches.group(0), pattern, 1))

        return ' '.join(results)

    def parse_surround_char(self, pattern, line):
        surround_char = re.search(pattern, line)
        if surround_char:
            return surround_char.group(1)
        else:
            return '/'

    def parse_match(self, line):
        surround_char = self.parse_surround_char(r'match\s+(.)', line)
        matches = re.search(r'match\s+[{0}]([^{0}]*)[{0}]'.format(surround_char), line)
        if matches is None:
            return ' '

        line = matches.group(1)
        line = self.parse_pairs(line)
        line = self.parse_specials(line)

        return line

    def parse_region(self, line):
        surround_char = self.parse_surround_char(r'start=(.)', line)
        starts = re.findall(r'start=[{0}]([^{0}]*)[{0}]'.format(surround_char), line)
        for i in range(len(starts)):
            starts[i] = self.parse_pairs(starts[i])
            starts[i] = self.parse_specials(starts[i])

        surround_char = self.parse_surround_char(r'skip=(.)', line)
        skips = re.findall(r'skip=[{0}]([^{0}]*)[{0}]'.format(surround_char), line)
        for i in range(len(skips)):
            skips[i] = self.parse_pairs(skips[i])
            skips[i] = self.parse_specials(skips[i])

        surround_char = self.parse_surround_char(r'end=(.)', line)
        ends = re.findall(r'end=[{0}]([^{0}]*)[{0}]'.format(surround_char), line)
        for i in range(len(ends)):
            ends[i] = self.parse_pairs(ends[i])
            ends[i] = self.parse_specials(ends[i])

        line = ' '.join(starts + skips + ends)
        return line

    def on_event(self, context: UserContext) -> None:
        if context['filetype'] in self.included_syntax:
            return

        syntax_candidates = [{'word': x} for x in
            self.parse_syntax(context)]
        syntax_candidates = sorted(syntax_candidates, key=lambda x: x['word'].swapcase())
        self.included_syntax[context['filetype']] = syntax_candidates

    def gather_candidates(self, context: UserContext) -> Candidates:
        return self.included_syntax.get(context['filetype'], [])

    def dump_syntax_candidates(self, candidates, path):
        keywords = [x['word'] for x in candidates]
        keywords = sorted(keywords)
        with open(path, 'w') as fid:
            for keyword in keywords:
                print(keyword, file=fid)
