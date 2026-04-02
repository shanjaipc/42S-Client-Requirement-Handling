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


def render_poc_guide():
    _D3_INLINE = _load_d3_inline()
    page_title("Task POC Guide", "Who to contact for every task type. Colour-coded by responsible team.")
    st.markdown("""<div style="background:white;border:1px solid #e5e7eb;border-radius:10px;padding:10px 20px;margin-bottom:14px;display:flex;gap:22px;flex-wrap:wrap;align-items:center;font-size:0.82rem;box-shadow:0 1px 4px rgba(0,0,0,0.04);font-family:'Inter',sans-serif;"><span style="color:#3b82f6;font-weight:600;">&#9646; Shanjai / Srinivas</span><span style="color:#7c3aed;font-weight:600;">&#9646; Dev Team</span><span style="color:#d97706;font-weight:600;">&#9646; Platform</span><span style="color:#dc2626;font-weight:600;">&#9646; TPM</span><span style="color:#16a34a;font-weight:600;">&#9646; DS / QA / Product</span></div>""", unsafe_allow_html=True)
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
<div id="legend"><b>Point of Contact</b><br><span style='color:#3b82f6'>&#9646;</span> Shanjai / Srinivas<br><span style='color:#7c3aed'>&#9646;</span> Dev Team<br><span style='color:#d97706'>&#9646;</span> Platform Team<br><span style='color:#dc2626'>&#9646;</span> TPM<br><span style='color:#16a34a'>&#9646;</span> DS / QA / Product</div>
<div id="hint">Scroll = zoom &nbsp;·&nbsp; Drag = pan &nbsp;·&nbsp; Click = expand/collapse</div>
{_D3_INLINE}
<script>
var data={name:"Task POC Guide",k:"root",children:[
{name:"Site Setup",k:"dev",children:[
  {name:"New site needed",k:"tpm",children:[
    {name:"Contact: TPM",k:"tpm"},
    {name:"Provide: name + index"},
    {name:"PSS created by TPM"},
    {name:"Dev does setup after"}
  ]},
  {name:"Reuse existing site",k:"dev",children:[
    {name:"Contact: Dev team",k:"dev"},
    {name:"Add seed URLs only"},
    {name:"OK even if site active"}
  ]},
  {name:"Naming convention",k:"sh",children:[
    {name:"Contact: Shanjai",k:"sh"},
    {name:"Ref: 42S Documentation"},
    {name:"domain_tld{#}_{idx}_42s"}
  ]},
  {name:"Domain mapping JSON",k:"dev",children:[
    {name:"Contact: Dev team",k:"dev"},
    {name:"domain_numbered_sites"},
    {name:"_mapping.json"}
  ]}
]},
{name:"Schema & Fields",k:"plat",children:[
  {name:"New field addition",k:"plat",children:[
    {name:"Contact: Platform team",k:"plat"},
    {name:"Finalise name + type"},
    {name:"Platform updates DRL"},
    {name:"Then Dev implements"},
    {name:"Eg: weekly_units_sold"}
  ]},
  {name:"DRL / EXT changes",k:"dev",children:[
    {name:"Contact: Dev team",k:"dev"},
    {name:"After Platform mapping"}
  ]},
  {name:"Schema review",k:"sh",children:[
    {name:"Contact: Shanjai/Dev",k:"sh"},
    {name:"Check 42S schema sheet"}
  ]}
]},
{name:"Crawl Issues",k:"dev",children:[
  {name:"Crawl not running",k:"dev",children:[
    {name:"Contact: Dev → TPM",k:"dev"},
    {name:"Check crawl-board logs"},
    {name:"Check proxy status"}
  ]},
  {name:"Count mismatch",k:"sh",children:[
    {name:"Contact: Shanjai/Srinivas",k:"sh"},
    {name:"Kibana vs Crawlboard"},
    {name:"Check logstash logs"},
    {name:"Threshold sheet review"}
  ]},
  {name:"Proxy failures",k:"sh",children:[
    {name:"Contact: Srinivas/Shanjai",k:"sh"},
    {name:"proxy_overview dash"},
    {name:"Oxylabs premium check"}
  ]},
  {name:"Extraction errors",k:"dev",children:[
    {name:"Contact: Dev team",k:"dev"},
    {name:"XPath / JS page issues"},
    {name:"lbhdf12/13 logstash"}
  ]}
]},
{name:"Client Requirements",k:"sh",children:[
  {name:"New client intake",k:"sh",children:[
    {name:"Contact: Shanjai",k:"sh"},
    {name:"Classify seed URLs"},
    {name:"Feasibility check"},
    {name:"Coordinate with product"}
  ]},
  {name:"New Balance",k:"sh",children:[
    {name:"Image download: Shanjai",k:"sh"},
    {name:"Server upload: Platform",k:"plat"},
    {name:"Product matching: DS",k:"ds"},
    {name:"QA annotation: QA team",k:"ds"},
    {name:"New fields: Platform",k:"plat"}
  ]},
  {name:"RamyBrook",k:"dev",children:[
    {name:"JSON mapping: Dev",k:"dev"},
    {name:"Saks cart flow: Dev",k:"dev"},
    {name:"Python-Ruby: Dev",k:"dev"},
    {name:"Validation: DS+QA",k:"ds"}
  ]},
  {name:"Client escalation",k:"tpm",children:[
    {name:"Contact: TPM",k:"tpm"},
    {name:"TPM → Mgmt if needed"}
  ]}
]},
{name:"Cost & Infra",k:"plat",children:[
  {name:"Monthly cost report",k:"plat",children:[
    {name:"Contact: Platform+DevOps",k:"plat"},
    {name:"Generates infra spend"},
    {name:"Manually indexed to ES"}
  ]},
  {name:"Clientwise analysis",k:"sh",children:[
    {name:"Contact: Shanjai",k:"sh"},
    {name:"42s Clientwise sheet"},
    {name:"Current vs prev cycle"}
  ]},
  {name:"Sitewise analysis",k:"sh",children:[
    {name:"Contact: Shanjai",k:"sh"},
    {name:"42s Sitewise sheet"}
  ]},
  {name:"InfraCost input",k:"sh",children:[
    {name:"Contact: Shanjai/Srinivas",k:"sh"},
    {name:"42s input data sheet"}
  ]}
]},
{name:"Maintenance Tasks",k:"sh",children:[
  {name:"Weekly checks",k:"sh",children:[
    {name:"Contact: Shanjai/Srinivas",k:"sh"},
    {name:"Disk, Proxy, Extraction"},
    {name:"Image counts"}
  ]},
  {name:"Monthly reports",k:"sh",children:[
    {name:"Contact: Shanjai/Srinivas",k:"sh"},
    {name:"Retrospection doc"},
    {name:"Cost analysis sheets"}
  ]},
  {name:"On-demand updates",k:"sh",children:[
    {name:"Contact: Shanjai",k:"sh"},
    {name:"New site threshold"},
    {name:"Mapping sheet update"}
  ]}
]},
{name:"Escalation Path",k:"tpm",children:[
  {name:"Platform change",k:"plat",children:[
    {name:"Contact: Platform team",k:"plat"},
    {name:"Schema / DRL / infra"}
  ]},
  {name:"New site creation",k:"tpm",children:[
    {name:"Contact: TPM",k:"tpm"},
    {name:"PSS → Dev setup"}
  ]},
  {name:"Client SLA issue",k:"tpm",children:[
    {name:"Contact: TPM",k:"tpm"},
    {name:"TPM → Management"}
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

var KF={root:"#1f2937",sh:"#dbeafe",dev:"#ede9fe",plat:"#fef3c7",tpm:"#fee2e2",ds:"#dcfce7"};
var KB={root:"#111827",sh:"#3b82f6",dev:"#7c3aed",plat:"#d97706",tpm:"#dc2626",ds:"#16a34a"};
var KT={root:"#fff",sh:"#1e40af",dev:"#5b21b6",plat:"#92400e",tpm:"#991b1b",ds:"#14532d"};
function nFill(d){if(d.depth===0)return KF.root;return KF[d.data.k]||"#f3f4f6";}
function nBorder(d){if(d.depth===0)return KB.root;return KB[d.data.k]||"#d1d5db";}
function nText(d){if(d.depth===0)return KT.root;return KT[d.data.k]||"#374151";}
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
