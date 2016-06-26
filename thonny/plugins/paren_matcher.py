from thonny.globals import get_workbench
import tokenize
import io
from thonny.codeview import CodeViewText
from thonny.shell import ShellText


_OPENERS = {')': '(', ']': '[', '}': '{'}

class ParenMatcher:

    def __init__(self, text):
        self.text = text
        self._configure_tags()

    def update_highlighting(self):
        start_index = "1.0"
        end_index = self.text.index("end")
        remaining = self._highlight_surrounding(start_index, end_index)
        self._highlight_unclosed(remaining, start_index, end_index)
    
    def _configure_tags(self):
        self.text.tag_configure("SURROUNDING_PARENS",
                                foreground="Blue", 
                                font=get_workbench().get_font("BoldEditorFont"))
        
        self.text.tag_configure("UNCLOSED", background="LightGray")
        
        self.text.tag_lower("UNCLOSED")
        self.text.tag_raise("sel")
        

    def _highlight_surrounding(self, start_index, end_index):
        self.text.tag_remove("SURROUNDING_PARENS", start_index, end_index)
        open_index, close_index, remaining = self._find_surrounding(start_index, end_index)
        if None not in [open_index, close_index]:
            self.text.tag_add("SURROUNDING_PARENS", open_index)
            self.text.tag_add("SURROUNDING_PARENS", close_index)
        
        return remaining

    # highlights an unclosed bracket
    def _highlight_unclosed(self, remaining, start_index, end_index):
        self.text.tag_remove("UNCLOSED", start_index, end_index)

        # anything remaining in the stack is an unmatched opener
        # since the list is ordered, we can highlight everything starting from the first element
        if len(remaining) > 0:
            opener = remaining[0]
            open_index = "%d.%d" % (opener.start[0], opener.start[1])
            self.text.tag_add("UNCLOSED", open_index, end_index) 
    
    def _get_paren_tokens(self, source):
        result = []
        try: 
            tokens = tokenize.tokenize(io.BytesIO(source.encode('utf-8')).readline)
            for token in tokens:
                if token.string != "" and token.string in "()[]{}":
                    result.append(token)
        except tokenize.TokenError:
            # happens eg when parens are unbalanced
            pass
        
        return result

    def _find_surrounding(self, start_index, end_index):
                
        stack = []
        opener, closer = None, None
        open_index, close_index = None, None
        
        start_row, start_col = map(int, start_index.split(".")) 
        source = self.text.get(start_index, end_index)
        
        # prepend source with empty lines and spaces to make 
        # token rows and columns match with widget indices
        source = ("\n" * (start_row-1)) + (" "*start_col) + source 
        
        for t in self._get_paren_tokens(source):
            if t.string == "" or t.string not in "()[]{}":
                continue
            if t.string in "([{":
                stack.append(t)
            elif len(stack) > 0:
                if stack[-1].string != _OPENERS[t.string]:
                    continue
                if not closer:
                    opener = stack.pop()
                    open_index = "%d.%d" % (opener.start[0], opener.start[1])
                    token_index = "%d.%d" % (t.start[0], t.start[1])
                    if self._is_insert_between_indices(open_index, token_index):
                        closer = t
                        close_index = token_index
                else:
                    stack.pop()
        
        return open_index, close_index, stack
        

    def _is_insert_between_indices(self, index1, index2):
        return self.text.compare("insert", ">=", index1) and \
               self.text.compare("insert-1c", "<=", index2)

class ShellParenMatcher(ParenMatcher):
    def update_highlighting(self):
        # TODO: check that cursor is in this range
        index_parts = self.text.tag_prevrange("command", "end")
        
        if index_parts:
            remaining = self._highlight_surrounding(*index_parts)
            self._highlight_unclosed(remaining, index_parts[0], "end")

def update_highlighting(event=None):
    text = event.widget
    if not hasattr(text, "paren_matcher"):
        if isinstance(text, CodeViewText):
            text.paren_matcher = ParenMatcher(text)
        elif isinstance(text, ShellText):
            text.paren_matcher = ShellParenMatcher(text)
        else:
            return
    
    text.paren_matcher.update_highlighting()

def load_plugin():
    wb = get_workbench()  
    
    wb.bind_class("CodeViewText", "<<CursorMove>>", update_highlighting, True)
    wb.bind_class("CodeViewText", "<<TextChange>>", update_highlighting, True)
    wb.bind_class("ShellText", "<<CursorMove>>", update_highlighting, True)
    wb.bind_class("ShellText", "<<TextChange>>", update_highlighting, True)
