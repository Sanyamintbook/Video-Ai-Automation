import os
from app.infrastructure.rag.vector_store import LocalVectorStore

def test_local_vector_store_workflow(tmp_path):
    store = LocalVectorStore()
    
    docs = [
        "Atmospheric pressure is the force exerted by the weight of air.",
        "Wind is the movement of air from high pressure to low pressure areas.",
        "A cyclone is a system of winds rotating inwards to an area of low barometric pressure.",
    ]
    
    store.add_documents(docs)
    
    # Test similarity search
    results = store.similarity_search("What causes wind?", top_k=1)
    assert len(results) == 1
    assert "Wind is the movement" in results[0]
    
    # Test save and load
    save_dir = os.path.join(tmp_path, "faiss_test")
    store.save(save_dir)
    
    # Load into a new store
    loaded_store = LocalVectorStore()
    loaded_store.load(save_dir)
    
    # Verify Loaded Store works the same
    loaded_results = loaded_store.similarity_search("cyclone wind rotation", top_k=1)
    assert len(loaded_results) == 1
    assert "cyclone is a system" in loaded_results[0]
