import streamlit as st  # type: ignore
import streamlit.components.v1 as components  # type: ignore
from pathlib import Path

from ui_helpers import page_title


def _load_d3_inline():
    """Load D3 from local file or fall back to CDN."""
    _path = Path("d3.v7.min.js")
    if _path.exists():
        return f"<script>{_path.read_text()}</script>"
    return '<script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>'


def render_ops_map():
    _D3_INLINE = _load_d3_inline()
    page_title("Day-to-Day Operations Mind Map", "All 7 operational areas — expand any branch to explore tasks & tools.")
    st.markdown("""<div style="background:white;border:1px solid #e5e7eb;border-radius:10px;padding:10px 20px;margin-bottom:14px;font-size:0.82rem;color:#6b7280;box-shadow:0 1px 4px rgba(0,0,0,0.04);font-family:'Inter',sans-serif;">7 operational areas &mdash; expand any branch &nbsp;&middot;&nbsp; scroll to zoom &nbsp;&middot;&nbsp; drag to pan</div>""", unsafe_allow_html=True)
    _html = """<!DOCTYPE html><meta charset="utf-8">
<style>
html,body{margin:0;padding:0;width:100vw;height:100vh;overflow:hidden;
  background:#f0f2f6;font-family:'Inter','Segoe UI',-apple-system,sans-serif;}
#tree{width:100vw;height:100vh;}
.node rect{stroke-width:1.8px;transition:all .18s;cursor:pointer;}
.node rect:hover{opacity:.82;}
.node text{pointer-events:none;font-weight:500;}
.link{fill:none;stroke-width:1.6px;opacity:.4;}
#legend{position:absolute;top:12px;right:14px;background:rgba(255,255,255,.93);
  border:1px solid #e5e7eb;border-radius:9px;padding:10px 14px;
  font-size:12px;color:#374151;line-height:2.1;
  box-shadow:0 2px 8px rgba(0,0,0,.07);}
#hint{position:absolute;bottom:10px;right:14px;font-size:10px;color:#9ca3af;}
</style>
<div id="tree"></div>
<div id="legend"><b>Operational Areas</b><br><span style='color:#2563eb'>&#9646;</span> Kibana Monitoring<br><span style='color:#059669'>&#9646;</span> Input Sheets<br><span style='color:#d97706'>&#9646;</span> Cost Analysis<br><span style='color:#7c3aed'>&#9646;</span> Crawl Health<br><span style='color:#dc2626'>&#9646;</span> Mapping & Tracking<br><span style='color:#0891b2'>&#9646;</span> Maintenance<br><span style='color:#be185d'>&#9646;</span> Automation<br></div>
<div id="hint">Scroll = zoom &nbsp;·&nbsp; Drag = pan &nbsp;·&nbsp; Click = expand/collapse</div>
{_D3_INLINE}
<script>
var data={name:"Daily Operations Hub",children:[
{name:"Kibana Monitoring",children:[
  {name:"Client vs Site",children:[
    {name:"Active clients list"},
    {name:"Crawl frequency"},
    {name:"Records by site"},
    {name:"Client % share/site"}
  ]},
  {name:"Proxy Status",children:[
    {name:"Success/fail rate"},
    {name:"Oxylabs premium"},
    {name:"Weekly check"}
  ]},
  {name:"Disk Time Opt.",children:[
    {name:"Slow sites identify"},
    {name:"Infinity loop detect"},
    {name:"Weekly + on-demand"}
  ]},
  {name:"Extraction Duration",children:[
    {name:"Slow parsers"},
    {name:"XPath bottlenecks"},
    {name:"Weekly check"}
  ]},
  {name:"Cost Analytics",children:[
    {name:"Client vs Site dash"},
    {name:"Monthly infra cost"},
    {name:"% data per client"}
  ]}
]},
{name:"Input Sheet Mgmt",children:[
  {name:"Data Request Format",children:[
    {name:"Client URLs + pincodes"},
    {name:"Crawl scheduling"},
    {name:"pincode_uniq_id logic"},
    {name:"Closed clients view"},
    {name:"Kibana link viewer"}
  ]},
  {name:"Add / Update URLs",children:[
    {name:"Sheet-based input"},
    {name:"ES-based input"},
    {name:"Pincode CSV input"}
  ]},
  {name:"AppScript Automation",children:[
    {name:"Auto crawl tracking"},
    {name:"Threshold alerts"},
    {name:"Status updates"}
  ]}
]},
{name:"Cost Analysis",children:[
  {name:"Clientwise (Monthly)",children:[
    {name:"Current vs prev cycle"},
    {name:"n-month trend"},
    {name:"42s Clientwise sheet"}
  ]},
  {name:"Sitewise (Monthly)",children:[
    {name:"Cost per site"},
    {name:"% data per client"},
    {name:"42s Sitewise sheet"}
  ]},
  {name:"InfraCost Input",children:[
    {name:"Platform + DevOps"},
    {name:"Manual ES indexing"},
    {name:"42s input data sheet"}
  ]}
]},
{name:"Crawl Health",children:[
  {name:"Count Mismatch",children:[
    {name:"Kibana vs Crawlboard"},
    {name:"Threshold sheet"},
    {name:"42S avg threshold"}
  ]},
  {name:"Failure Logs",children:[
    {name:"lbhdf12_logstash.log"},
    {name:"lbhdf13_logstash.log"},
    {name:"Copied hourly to ex51"}
  ]},
  {name:"Misc + Dep Sites",children:[
    {name:"Misc processing tracker"},
    {name:"Dep data upload tracker"},
    {name:"Banner sites progress"}
  ]}
]},
{name:"Mapping & Tracking",children:[
  {name:"Client-Site Mapping",children:[
    {name:"Client to site view"},
    {name:"Site to client view"},
    {name:"Active sites list"}
  ]},
  {name:"Domain Mapping JSON",children:[
    {name:"Products to Trends link"},
    {name:"domain_numbered_sites"},
    {name:"Update on new site"}
  ]},
  {name:"42S Schema Sheet",children:[
    {name:"Field definitions"},
    {name:"Must-have fields"},
    {name:"Index-specific fields"}
  ]}
]},
{name:"Maintenance",children:[
  {name:"Weekly Tasks",children:[
    {name:"Disk time review"},
    {name:"Extraction duration"},
    {name:"Proxy health check"},
    {name:"Image count check"}
  ]},
  {name:"Monthly Tasks",children:[
    {name:"Retrospection doc"},
    {name:"Aggregated report"},
    {name:"Clientwise cost"},
    {name:"Sitewise cost"}
  ]},
  {name:"On-Demand Tasks",children:[
    {name:"New site addition"},
    {name:"Client pause/resume"},
    {name:"Threshold updates"},
    {name:"InfraCost update"}
  ]}
]},
{name:"Automation",children:[
  {name:"Google App Scripts",children:[
    {name:"Data Request Format"},
    {name:"Clientwise cost"},
    {name:"Sitewise cost"},
    {name:"Threshold alerts"}
  ]},
  {name:"Ruby Scripts",children:[
    {name:"Volume adjustment"},
    {name:"Missing upload check"},
    {name:"Weekly crawl tracker"}
  ]}
]}
]};
var NW=196,NH=48,NR=9;
var M={top:60,right:240,bottom:60,left:210};
var W=window.innerWidth-M.left-M.right;
var H=window.innerHeight-M.top-M.bottom;
var svg=d3.select("#tree").append("svg")
  .attr("width",W+M.left+M.right).attr("height",H+M.top+M.bottom)
  .call(d3.zoom().scaleExtent([.18,3]).on("zoom",e=>g.attr("transform",e.transform)))
  .on("dblclick.zoom",null);
var g=svg.append("g").attr("transform","translate("+M.left+","+(M.top+H/2)+")");
var i=0,dur=400;
var root=d3.hierarchy(data);
root.x0=0;root.y0=0;
var BC=["#2563eb", "#059669", "#d97706", "#7c3aed", "#dc2626", "#0891b2", "#be185d"];
function getBC(d){
  var a=d;while(a.depth>1&&a.parent)a=a.parent;
  if(a.depth===0)return"#1f2937";
  return BC[(a.parent?a.parent.children.indexOf(a):0)%BC.length];
}
function nFill(d){
  if(d.depth===0)return"#1f2937";
  if(d.depth===1){var c=getBC(d);return c+"18";}
  return"#f3f4f6";
}
function nBorder(d){return getBC(d);}
function nText(d){
  if(d.depth===0)return"#fff";
  if(d.depth===1)return getBC(d);
  return"#374151";
}
root.children.forEach(collapse);
update(root);
function collapse(d){if(d.children){d._children=d.children;d._children.forEach(collapse);d.children=null;}}
function wrap(t,n){if(t.length<=n)return[t];var m=t.lastIndexOf(" ",n);if(m<1)m=n;return[t.slice(0,m),t.slice(m+1)];}
function update(src){
  var tree=d3.tree().nodeSize([NH+28,1]);
  var td=tree(root);
  var nodes=td.descendants(),links=td.descendants().slice(1);
  var colW=Math.max(NW+36,W/5.4);nodes.forEach(d=>d.y=d.depth*colW);
  var node=g.selectAll("g.node").data(nodes,d=>d.id||(d.id=++i));
  var ne=node.enter().append("g").attr("class","node")
    .attr("transform",()=>"translate("+src.y0+","+src.x0+")")
    .on("click",click);
  ne.append("rect")
    .attr("width",NW).attr("height",NH).attr("x",-NW/2).attr("y",-NH/2)
    .attr("rx",NR).attr("ry",NR)
    .style("fill",d=>nFill(d)).style("stroke",d=>nBorder(d))
    .style("filter","drop-shadow(0 2px 5px rgba(0,0,0,.07))");
  ne.each(function(d){
    var el=d3.select(this),ln=wrap(d.data.name,23);
    var dy1=ln.length===1?"0.35em":"-0.5em", dy2="0.82em";
    el.append("text").attr("dy",dy1).attr("text-anchor","middle")
      .style("font-size","13px").style("fill",nText(d)).text(ln[0]);
    if(ln.length>1)
      el.append("text").attr("dy",dy2).attr("text-anchor","middle")
        .style("font-size","12px").style("fill",nText(d)).text(ln[1]);
  });
  ne.append("text").attr("class","ind")
    .attr("dy","0.35em").attr("x",NW/2-9).attr("text-anchor","middle")
    .style("font-size","9px");
  var nu=ne.merge(node);
  nu.transition().duration(dur).attr("transform",d=>"translate("+d.y+","+d.x+")");
  nu.select("rect").style("fill",d=>nFill(d)).style("stroke",d=>nBorder(d));
  nu.select(".ind")
    .text(d=>(d._children||d.children)?"●":"")
    .style("fill",d=>nBorder(d))
    .style("opacity",d=>(d._children||d.children)?1:0);
  node.exit().transition().duration(dur)
    .attr("transform",()=>"translate("+src.y+","+src.x+")").remove();
  var link=g.selectAll("path.link").data(links,d=>d.id);
  var le=link.enter().insert("path","g").attr("class","link")
    .attr("d",()=>{var o={x:src.x0,y:src.y0};return diag(o,o);})
    .style("stroke",d=>nBorder(d));
  le.merge(link).transition().duration(dur).attr("d",d=>diag(d,d.parent));
  link.exit().transition().duration(dur)
    .attr("d",()=>{var o={x:src.x,y:src.y};return diag(o,o);}).remove();
  nodes.forEach(d=>{d.x0=d.x;d.y0=d.y;});
}
function diag(s,d){
  return"M"+s.y+" "+s.x+" C"+(s.y+d.y)/2+" "+s.x+","+(s.y+d.y)/2+" "+d.x+","+d.y+" "+d.x;
}
function click(e,d){
  if(d.children){d._children=d.children;d.children=null;}
  else{d.children=d._children;d._children=null;}
  update(d);
}
</script>"""
    st.caption("💡 Click nodes to expand/collapse · Scroll to zoom · Drag to pan · Reload if diagram is blank")
    components.html(_html.replace("{_D3_INLINE}", _D3_INLINE), height=1000, scrolling=False)
