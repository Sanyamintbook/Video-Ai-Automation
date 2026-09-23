import re
from typing import List

class RecursiveCharacterTextSplitter:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 150):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_text(self, text: str) -> List[str]:
        if not text:
            return []
            
        chunks = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            end = min(start + self.chunk_size, text_len)
            
            # Try to find a logical boundary near the end of the chunk
            if end < text_len:
                # Look back up to 200 characters for structural boundaries
                lookback_start = max(start, end - 200)
                lookback = text[lookback_start:end]
                best_split = -1
                
                # Check for paragraph boundary
                double_nl = lookback.rfind("\n\n")
                if double_nl != -1:
                    best_split = double_nl + 2
                else:
                    # Check for newline boundary
                    single_nl = lookback.rfind("\n")
                    if single_nl != -1:
                        best_split = single_nl + 1
                    else:
                        # Check for sentence end
                        period = lookback.rfind(". ")
                        if period != -1:
                            best_split = period + 2
                            
                if best_split != -1:
                    end = max(start, lookback_start + best_split)
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
                
            # If the end reached the end of the text, we're done
            if end >= text_len:
                break
                
            # Move the window forward, maintaining overlap
            next_start = end - self.chunk_overlap
            # Prevent infinite loops in case window doesn't progress
            if next_start <= start:
                start = end
            else:
                start = next_start
                
        return chunks
