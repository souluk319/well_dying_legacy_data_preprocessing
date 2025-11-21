import unittest
from preprocess_pdfs import chunk_simple, chunk_law

class TestChunking(unittest.TestCase):
    def test_chunk_simple_overlap(self):
        # Create a text that is longer than 500 chars to force splitting
        # Create a text that is longer than 500 chars to force splitting
        # Use sentences so it can be split
        s1 = "A" * 40 + "."
        s2 = "B" * 40 + "."
        # We need enough sentences to exceed 500 + 300 = 800 chars
        # 41 * 25 = 1025 chars
        text = " ".join([s1 if i % 2 == 0 else s2 for i in range(25)])
        
        # Mock config
        source = "test_doc"
        category = "test_cat"
        prefix = "test"
        
        # Run chunking with overlap
        chunks = chunk_simple(text, source, category, prefix, overlap=20)
        
        # Check if we have multiple chunks
        self.assertTrue(len(chunks) > 1)
        
        # Check overlap
        # The end of the first chunk should match the beginning of the second chunk (approx)
        chunk1_text = chunks[0]['text']
        chunk2_text = chunks[1]['text']
        
        # We expect some overlap. 
        # Since the logic is: buf = buf[-overlap:] + ...
        # The second chunk should start with the last 'overlap' chars of the previous buffer state.
        
        # Let's print to see (for manual verification in output)
        print(f"\nChunk 1 end: ...{chunk1_text[-30:]}")
        print(f"Chunk 2 start: {chunk2_text[:30]}...")
        
        # Basic assertion: chunk 2 should contain a part of chunk 1
        # Note: clean_chunk_text might modify spaces, so we check substring presence carefully
        overlap_text = chunk1_text[-20:]
        self.assertIn(overlap_text, chunk2_text)

if __name__ == '__main__':
    unittest.main()
