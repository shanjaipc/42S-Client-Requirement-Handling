import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(layout="wide")

html_code = """
<!DOCTYPE html>
<meta charset="utf-8">

<style>

html, body{
    margin:0;
    padding:0;
    width:100vw;
    height:100vh;
    overflow:hidden;
    background:#ffffff;
    font-family:"Segoe UI", sans-serif;
}

#tree{
    width:100vw;
    height:100vh;
}

.node rect{
    fill:#f3edff;
    stroke:#9c8cff;
    stroke-width:2px;
    rx:8;
    ry:8;
    filter: drop-shadow(0px 6px 10px rgba(120,90,200,0.2));
}

.node rect:hover{
    fill:#e9e1ff;
    stroke:#7d6bff;
}

.node text{
    font-size:14px;
    fill:#3a2f66;
    pointer-events:none;
}

.link{
    fill:none;
    stroke:#c7bcff;
    stroke-width:2px;
}

</style>

<div id="tree"></div>

<script src="https://d3js.org/d3.v7.min.js"></script>

<script>

var data = {
 name: "Tasks",
 children: [
    {
        name:"Site Setup Namings",
        children:[
            {
                name:"Domain Already Exists",
                children:[
                    {
                        name:"Depth 4"
                    }
                ]
            }
        ]
    },
    {
        name:"Choosing Index",
        children:[
            {
                name:"Domain Already",
                children:[
                    {
                        name:"Depth 4"
                    }
                ]
            }
        ]
    },
    {
        name:"Value Reprocessing",
        children:[
            {
                name:"Domain Already",
                children:[
                    {
                        name:"Depth 4"
                    }
                ]
            }
        ]
    },
    {
        name:"Point Of Contact",
        children:[
            {
                name:"Domain Already",
                children:[
                    {
                        name:"Depth 4"
                    }
                ]
            }
        ]
    },
 ]
};

var margin = {top:50,right:120,bottom:50,left:120}

var width = window.innerWidth - margin.left - margin.right
var height = window.innerHeight - margin.top - margin.bottom

var svg = d3.select("#tree")
 .append("svg")
 .attr("width",width + margin.left + margin.right)
 .attr("height",height + margin.top + margin.bottom)
 .append("g")
 .attr("transform","translate("+margin.left+","+margin.top+")")

var i = 0
var duration = 600

var root = d3.hierarchy(data)

root.x0 = height/2
root.y0 = 0

root.children.forEach(collapse)

update(root)

function collapse(d){
 if(d.children){
  d._children = d.children
  d._children.forEach(collapse)
  d.children = null
 }
}

function update(source){

 var tree = d3.tree().size([height,width])
 var treeData = tree(root)

 var nodes = treeData.descendants()
 var links = treeData.descendants().slice(1)

 nodes.forEach(function(d){
  d.y = d.depth * (width/6)
 })

 var node = svg.selectAll('g.node')
  .data(nodes,function(d){ return d.id || (d.id = ++i) })

 var nodeEnter = node.enter()
  .append('g')
  .attr('class','node')
  .attr("transform",function(){
    return "translate("+source.y0+","+source.x0+")"
  })
  .on('click',click)

 nodeEnter.append('rect')
  .attr('width',170)
  .attr('height',42)
  .attr('x',-85)
  .attr('y',-21)

 nodeEnter.append('text')
  .attr("dy",".35em")
  .attr("text-anchor","middle")
  .text(function(d){ return d.data.name })

 var nodeUpdate = nodeEnter.merge(node)

 nodeUpdate.transition()
  .duration(duration)
  .attr("transform",function(d){
    return "translate("+d.y+","+d.x+")"
  })

 node.exit().remove()

 var link = svg.selectAll('path.link')
  .data(links,function(d){ return d.id })

 var linkEnter = link.enter()
  .insert('path',"g")
  .attr("class","link")
  .attr('d',function(){
    var o = {x:source.x0,y:source.y0}
    return diagonal(o,o)
  })

 linkEnter.merge(link)
  .transition()
  .duration(duration)
  .attr('d',function(d){ return diagonal(d,d.parent) })

 link.exit().remove()

 nodes.forEach(function(d){
  d.x0 = d.x
  d.y0 = d.y
 })

}

function diagonal(s,d){
 return `M ${s.y} ${s.x}
  C ${(s.y+d.y)/2} ${s.x},
    ${(s.y+d.y)/2} ${d.x},
    ${d.y} ${d.x}`
}

function click(event,d){
 if(d.children){
  d._children = d.children
  d.children = null
 } else {
  d.children = d._children
  d._children = null
 }
 update(d)
}

</script>
"""

components.html(html_code, height=1100, scrolling=False)