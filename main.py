import streamlit as st
import requests
from streamlit_flowide import GraphMap
import json
import math

SCL_URL = ""


mapConfig = {
}


@st.cache
def init():
    anchorsList = requests.get(SCL_URL
 + "/anchors?limit=10000").json()

    anchorIdToDevId = {}
    for anchor in anchorsList:
        anchorIdToDevId[anchor["anchorId"]] = anchor["devId"]

    tdoaanchorsetIds = requests.get(SCL_URL
 + "/tdoaanchorsets?fields=tdoaanchorsetId").json()

    if (len(tdoaanchorsetIds) != 1):
        print("Multiple Tdoaanchorsets not supported for now")
        exit()

    calibJson = requests.get(
        SCL_URL
     + "/tdoaanchorsets/" + tdoaanchorsetIds[0]["tdoaanchorsetId"] + "/tdoacalibgraph?fields=full").json()
    calibJsonGraph = calibJson["full"]["graph"]

    dpJson = requests.get(
        SCL_URL
     + "/tdoaanchorsets/" + tdoaanchorsetIds[0]["tdoaanchorsetId"] + "/directpathsgraph?fields=full").json()
    dpJsonGraph = dpJson["full"]["graph"]

    return (dpJsonGraph, calibJsonGraph, anchorIdToDevId)


def scl_graph_converter(sclGraph,uuid_to_devid,edge_metadata_transformer):
    graph = {'directed':False,'edges':[],'nodes':{}}

    id_to_pos = {}
    for node in sclGraph["nodes"]:
        pos = node["metadata"]["data"]["position"][0:2]
        pos_string = f"[{int(pos[0]) if pos[0].is_integer() else pos[0]},{int(pos[1]) if pos[1].is_integer() else pos[1]}]"
        graph['nodes'][pos_string] = {
            'label':uuid_to_devid[node["metadata"]["uuid"]],
            'metadata':{
                'display':{
                    'color':'green'
                }
            }
        }
        id_to_pos[node["id"]] = pos_string

    for edge in sclGraph["edges"]:
        graph["edges"].append({
             "source":id_to_pos[edge["source"]],
             "target":id_to_pos[edge["target"]],
             "label":edge["metadata"]["uuid"],
             "metadata":edge_metadata_transformer(edge["metadata"])
        })
    if 'directed' in sclGraph.keys():
        graph['directed'] = sclGraph['directed']

    return graph 

def hslArrayToHslString(hslArray):
    return 'hsl(' + str(hslArray[0]) + ',' + str(hslArray[1]) + '%,' + str(hslArray[2]) + '%)'

def lerpedColorGreenToRed(t):
    redHue = 0
    greenHue = 120
    return [
        ((1 - t) * greenHue) + t * redHue,
        100,
        50
    ]


def dp_graph_metadata_transformer(metadata):
    color = 'blue'
    weight = 2.;
    opacity = 1
    losConfidenceLevelByAnE = metadata.get('data',{}).get('losConfidenceLevelByAnBuffer',{}).get('E')
    if( losConfidenceLevelByAnE is not None ):
        color = hslArrayToHslString(lerpedColorGreenToRed(1 - losConfidenceLevelByAnE) )
    else:
        opacity = 0.1
    if (losConfidenceLevelByAnE == 1.0):
        weight *= 2.

    return {
        'display':{
            'color':color,
            'weight':weight,
            'opacity':opacity
        }
    }

def calib_graph_metadata_transformer(metadata):
    color = 'black'
    opacity = 1
    appliedVariance = metadata.get('data',{}).get('appliedVariance')
    if appliedVariance is not None:
        percent = min( math.sqrt( appliedVariance ) / 0.2 , 1.)
        color = hslArrayToHslString( lerpedColorGreenToRed(percent) )
    else:
        opacity = 0.1
    
    return {
        'display':{
            'color':color,
            'opacity':opacity
        }
    }



dpgraph,cgraph,anchor_id_map = init()

dp = scl_graph_converter(dpgraph,anchor_id_map,dp_graph_metadata_transformer)
calib = scl_graph_converter(cgraph,anchor_id_map,calib_graph_metadata_transformer)

st.header('Direct paths graph')
GraphMap(mapConfig,data=dp,key='dp')
st.header('Calibration graph')
GraphMap(mapConfig,data=calib, key='calib')
