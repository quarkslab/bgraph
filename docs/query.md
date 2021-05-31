# Example

This example assumes you have already created the BGraph for `android-10.0.0_r1` and the file is available in `graphs/android-10.0.0_r1.bgraph`.

## First query: dependencies of a source file

The patch for the CVE-2020-0471 modifies the file `packet_fragmenter.cc` ( commit: [ca6b0a](https://android.googlesource.com/platform/system/bt/+/ca6b0a211eb39ba85eed60ea740c85d1122fc6bc)). We are interested in the different targets (e.g. binaries and libraries) where we can find the content of this file in AOSP.

```bash
% bgraph query graphs/android-10.0.0_r1.bgraph --src 'packet_fragmenter.cc'
         Dependencies for source file          
             packet_fragmenter.cc              
               ╷                   ╷           
  Target       │ Type              │ Distance  
 ══════════════╪═══════════════════╪══════════ 
  libbt-hci    │ cc_library_static │ 1         
  libbt-stack  │ cc_library_static │ 2         
  libbluetooth │ cc_library_shared │ 2         
               ╵                   ╵           
```

!!! warning
    The example assumes you have already created the `bgraph` for `android-10.0.0_r1`.


## Second query: let's find sources of library

```bash
% bgraph query graphs/android-10.0.0_r1.bgraph --target libbluetooth-types-header                               
                           Sources for the target libbluetooth-types-header                            
                                                                                          ╷            
  Filename                                                                                │ File type  
 ═════════════════════════════════════════════════════════════════════════════════════════╪═══════════ 
  /tmp/bgraph_6p4534y2/android-10.0.0_r1/system/bt/types/class_of_device.h                │        .h  
  /tmp/bgraph_6p4534y2/android-10.0.0_r1/system/bt/types/test/bluetooth/uuid_unittest.cc  │       .cc  
  /tmp/bgraph_6p4534y2/android-10.0.0_r1/system/bt/types/bluetooth/uuid.h                 │        .h  
  /tmp/bgraph_6p4534y2/android-10.0.0_r1/system/bt/types/raw_address.cc                   │       .cc  
  /tmp/bgraph_6p4534y2/android-10.0.0_r1/system/bt/types/BUILD.gn                         │       .gn  
  /tmp/bgraph_6p4534y2/android-10.0.0_r1/system/bt/types/test/raw_address_unittest.cc     │       .cc  
  /tmp/bgraph_6p4534y2/android-10.0.0_r1/system/bt/types/Android.bp                       │       .bp  
  /tmp/bgraph_6p4534y2/android-10.0.0_r1/system/bt/types/bluetooth/uuid.cc                │       .cc  
  /tmp/bgraph_6p4534y2/android-10.0.0_r1/system/bt/types/test/class_of_device_unittest.cc │       .cc  
  /tmp/bgraph_6p4534y2/android-10.0.0_r1/system/bt/types/raw_address.h                    │        .h  
  /tmp/bgraph_6p4534y2/android-10.0.0_r1/system/bt/types/class_of_device.cc               │       .cc  
                                                                                          ╵            

```

!!! note
    This type of requests can leads to huge number of results and are not really suited for a command line usage. 
    For example, the result for the target query of `libbluetooth` yields to more than 5700 lines of results.

## Use as a library

`BGraph` is also a library and can be used like one.

!!! note 
    All the examples can be runned as-if assuming you are at the root directory of the project and a bgraph for `android-10.0.0_r1` is found in `graphs/`.

### Example
```python
import bgraph

# Load the graph
graph = bgraph.viewer.load_graph("graphs/android-10.0.0_r1.bgraph")

# Query to find the source dependencies of libbluetooth
sources = bgraph.viewer.find_sources(graph, "libbluetooth")
for source in filter(lambda x: 'zlib' in x, sources):
    print(f"Zlib file: {source}")
```

### Format results

```python
import bgraph
from bgraph.types import QueryType, OutChoice

# Load the graph
graph = bgraph.viewer.load_graph("graphs/android-10.0.0_r1.bgraph")
sources = bgraph.viewer.find_sources(graph, "libbluetooth")

bgraph.viewer.format_result(
    graph, sources, query=QueryType.TARGET, query_value="libbluetooth", out_choice=OutChoice.DOT
)

```


### Iterative process

In this example, we are looking for the first target using `Parcel.cpp`. This will illustrate both the `radius` argument of the `find_target` method and what to do when multiple files matches the name we are looking for.

```python
import bgraph

graph = bgraph.viewer.load_graph("graphs/android-10.0.0_r1.bgraph")

# Will raise an exception : TooManyNodes - refine the search
bgraph.viewer.find_target(graph, "Parcel.cpp", radius=1)

# Indeed, there are many sources files having "Parcel.cpp" in their name
graph_srcs = [node for node in graph if bgraph.viewer.get_node_type(node) == "source"]
potential_results = [node for node in graph_srcs if "Parcel.cpp" in node]
print(f"Found {len(potential_results)}/{len(graph_srcs)} matching nodes")

# In this case, it is possible to use a more precise path:
file, target = bgraph.viewer.find_target(graph, "libs/binder/Parcel.cpp", radius=1)
print(f"{file} is used in {target}") 
# file in this case will be the absolute path to the Parcel.cpp found.
```