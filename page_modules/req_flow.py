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


def render_req_flow():
    _D3_INLINE = _load_d3_inline()
    page_title("New Requirement Decision Tree", "Step-by-step guide from client intake to delivery. Click nodes to expand.")
    st.markdown("""<div style="background:white;border:1px solid #e5e7eb;border-radius:10px;padding:10px 20px;margin-bottom:14px;display:flex;gap:24px;flex-wrap:wrap;align-items:center;font-size:0.82rem;box-shadow:0 1px 4px rgba(0,0,0,0.04);font-family:'Inter',sans-serif;"><span style="color:#3b82f6;font-weight:600;">&#9646; Step</span><span style="color:#d97706;font-weight:600;">&#9646; Decision</span><span style="color:#22c55e;font-weight:600;">&#9646; Outcome</span><span style="color:#94a3b8;font-weight:600;">&#9646; Action</span><span style="color:#94a3b8;margin-left:auto;font-size:0.78rem;">8 sequential steps &mdash; intake to delivery</span></div>""", unsafe_allow_html=True)
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
<div id="legend"><b>Node Types</b><br><span style='color:#3b82f6'>&#9646;</span> Step &nbsp;<span style='color:#d97706'>&#9646;</span> Decision &nbsp;<span style='color:#22c55e'>&#9646;</span> Outcome &nbsp;<span style='color:#94a3b8'>&#9646;</span> Action</div>
<div id="hint">Scroll = zoom &nbsp;·&nbsp; Drag = pan &nbsp;·&nbsp; Click = expand/collapse</div>
{_D3_INLINE}
<script>
var data={name:"New Requirement Intake",k:"start",children:[
{name:"1. Finalise Domains",k:"step",children:[
  {name:"QCommerce",k:"act",children:[{name:"Swiggy Instamart"},{name:"ZeptoNow"},{name:"Blinkit"},{name:"BigBasket"}]},
  {name:"ECom",k:"act",children:[{name:"Amazon"},{name:"Flipkart"},{name:"Nykaa"},{name:"Purplle"}]},
  {name:"Fashion Retail",k:"act",children:[{name:"AJIO"},{name:"Myntra"}]}
]},
{name:"2. Classify Seed URLs",k:"step",children:[
  {name:"Category URL?",k:"dec",children:[
    {name:"PDP crawl",k:"out",children:[{name:"Products Index"},{name:"Trends Index"}]},
    {name:"Listing page",k:"out",children:[{name:"SOS Index"}]},
    {name:"Banner present",k:"out",children:[{name:"Misc Index"}]}
  ]},
  {name:"Direct Product URL?",k:"dec",children:[
    {name:"Trends Index only",k:"out"}
  ]},
  {name:"SOS Keyword input?",k:"dec",children:[
    {name:"SOS Index",k:"out",children:[{name:"No PDP fetch"},{name:"Listing page only"}]}
  ]},
  {name:"Reviews needed?",k:"dec",children:[
    {name:"Reviews Index",k:"out",children:[{name:"ES input from Products"}]}
  ]},
  {name:"Banner tracking?",k:"dec",children:[
    {name:"API available",k:"out",children:[{name:"Misc API crawl"}]},
    {name:"No API",k:"out",children:[{name:"Screenshot method"}]}
  ]}
]},
{name:"3. Index Decision",k:"step",children:[
  {name:"Zipcode based?",k:"dec",children:[
    {name:"YES: add _zipcode",k:"out"},
    {name:"NO: standard name",k:"out"}
  ]},
  {name:"Historical tracking?",k:"dec",children:[
    {name:"YES: Trends/SOS/Misc",k:"out"},
    {name:"NO: Products/Reviews",k:"out"}
  ]},
  {name:"Variants needed?",k:"dec",children:[
    {name:"YES: uniq_id/variant",k:"out"},
    {name:"NO: uniq_id/product",k:"out"}
  ]},
  {name:"Assign Domain #",k:"act",children:[
    {name:"Products: no number"},
    {name:"Sheet Hourly: #1"},
    {name:"ES Daily: #2"},
    {name:"ES Hourly: #3"},
    {name:"SOS / PV: #4"},
    {name:"Others: #5+"}
  ]}
]},
{name:"4. Feasibility Check",k:"step",children:[
  {name:"Check schema sheet",k:"act",children:[
    {name:"Must-have fields"},{name:"General feasibility"}
  ]},
  {name:"Special fields?",k:"dec",children:[
    {name:"YES: define + Platform",k:"out"},
    {name:"NO: proceed",k:"out"}
  ]},
  {name:"Blocking challenge?",k:"dec",children:[
    {name:"YES: raise flag early",k:"out"},
    {name:"NO: proceed",k:"out"}
  ]}
]},
{name:"5. Site Setup",k:"step",children:[
  {name:"Domain exists?",k:"dec",children:[
    {name:"YES: reuse (even active)",k:"out"},
    {name:"NO: ask TPM to create",k:"out"}
  ]},
  {name:"Define site name",k:"act",children:[
    {name:"domain_tld{#}{_zip}"},
    {name:"_{index}_forty_two_signals"}
  ]},
  {name:"Update mapping JSON",k:"act",children:[
    {name:"domain_numbered_sites"},
    {name:"_mapping.json"}
  ]}
]},
{name:"6. Dev Implementation",k:"step",children:[
  {name:"Products: RSS→DSK→EXT",k:"act",children:[
    {name:"uniq_id unique always"},
    {name:"internal_client_name"},
    {name:"joining_key required"},
    {name:"ISO date format only"}
  ]},
  {name:"Trends: inherit DSK+EXT",k:"act",children:[
    {name:"RSS changes only"},
    {name:"uniq_id unchanged"}
  ]},
  {name:"SOS: listing only",k:"act",children:[
    {name:"No PDP fetch"},
    {name:"Scroll / page limit"}
  ]}
]},
{name:"7. Post-Setup Checks",k:"step",children:[
  {name:"Dev QA all fields",k:"act"},
  {name:"Count match?",k:"dec",children:[
    {name:"Crawlboard = Kibana",k:"out"},
    {name:"Mismatch: check logs",k:"out"}
  ]},
  {name:"All records indexed?",k:"dec",children:[
    {name:"YES: QA phase",k:"out"},
    {name:"NO: debug logstash",k:"out"}
  ]}
]},
{name:"8. QA & Delivery",k:"step",children:[
  {name:"Products dashboard QA",k:"act"},
  {name:"Trends QA (after prod)",k:"act"},
  {name:"Kibana = Crawlboard?",k:"dec",children:[
    {name:"OK: share Kibana link",k:"out"},
    {name:"Fail: debug logstash",k:"out"}
  ]},
  {name:"QA passed?",k:"dec",children:[
    {name:"YES: deliver to client",k:"out"},
    {name:"NO: fix and re-QA",k:"out"}
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

var KF={start:"#1f2937",step:"#dbeafe",dec:"#fef3c7",out:"#dcfce7",act:"#f1f5f9"};
var KB={start:"#111827",step:"#3b82f6",dec:"#d97706",out:"#22c55e",act:"#94a3b8"};
var KT={start:"#fff",step:"#1e40af",dec:"#92400e",out:"#14532d",act:"#374151"};
function nFill(d){if(d.depth===0)return KF.start;return KF[d.data.k]||"#f3f4f6";}
function nBorder(d){if(d.depth===0)return KB.start;return KB[d.data.k]||"#d1d5db";}
function nText(d){if(d.depth===0)return KT.start;return KT[d.data.k]||"#374151";}
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
