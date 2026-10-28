// TaleBrush
// Copyright (c) 2022-present NAVER Corp.
// GPLv3

// Enhancement E6 (see REVIVAL_LOG.md): small numbered markers that open an explanation of a feature,
// with an example, for demos and first-time users. An optional note calls out what the revival changed or
// added on top of the 2022 original. Hide them all with ?markers=off in the URL.

import React from 'react';
import ReactDOM from 'react-dom';

const OPEN_EVENT = 'talebrush-demo-marker-open'
const CARD_WIDTH = 300
const markersOff = /[?&]markers=off\b/.test(window.location.search)

export default class TaleBrush_DemoMarker extends React.Component {

  constructor(props){
    super(props)
    this.state = {open: false, hover: false, top: null, bottom: null, left: 0}
    this.marker = React.createRef()
    this.closeIfOther = this.closeIfOther.bind(this)
    this.closeOnOutside = this.closeOnOutside.bind(this)
    this.closeOnEscape = this.closeOnEscape.bind(this)
  }

  componentDidMount(){
    window.addEventListener(OPEN_EVENT, this.closeIfOther)
  }

  componentWillUnmount(){
    window.removeEventListener(OPEN_EVENT, this.closeIfOther)
    this.stopListening()
  }

  // Only one explanation is open at a time.
  closeIfOther(e){
    if(e.detail!=this.props.n && this.state.open){
      this.close()
    }
  }

  closeOnOutside(e){
    if(this.card && this.card.contains(e.target)){
      return
    }
    if(this.marker.current && this.marker.current.contains(e.target)){
      return
    }
    this.close()
  }

  closeOnEscape(e){
    if(e.key=='Escape'){
      this.close()
    }
  }

  stopListening(){
    document.removeEventListener('pointerdown', this.closeOnOutside, true)
    document.removeEventListener('keydown', this.closeOnEscape)
  }

  close(){
    this.stopListening()
    this.setState({open: false})
  }

  toggle(e){
    e.stopPropagation()
    if(this.state.open){
      this.close()
      return
    }
    // The card is placed in viewport coordinates and kept on screen: below the marker,
    // or above it when the marker is near the bottom of the window.
    var rect = this.marker.current.getBoundingClientRect()
    var left = Math.max(12, Math.min(rect.left - 12, window.innerWidth - CARD_WIDTH - 12))
    var below = window.innerHeight - rect.bottom
    var top = null, bottom = null
    if(below < 340 && rect.top > below){
      bottom = window.innerHeight - rect.top + 8
    }else{
      top = rect.bottom + 8
    }
    window.dispatchEvent(new CustomEvent(OPEN_EVENT, {detail: this.props.n}))
    document.addEventListener('pointerdown', this.closeOnOutside, true)
    document.addEventListener('keydown', this.closeOnEscape)
    this.setState({open: true, top, bottom, left})
  }

  // Keep pointer events away from the drawing area and the page's own handlers.
  stop(e){
    e.stopPropagation()
  }

  renderCard(){
    return ReactDOM.createPortal(
      <div ref={(el)=>{this.card = el}} onPointerDown={this.stop} onPointerUp={this.stop} onPointerMove={this.stop}
        style={Object.assign({position: 'fixed', left: this.state.left, width: CARD_WIDTH+'px', zIndex: 1000, overflowY: 'auto',
          backgroundColor: 'white', borderRadius: '10px', padding: '14px 16px',
          boxShadow: '0 6px 24px rgba(0, 0, 0, 0.18)', border: '1px solid #e6e6e6',
          fontFamily: 'Noto Sans', fontSize: '13.5px', lineHeight: '150%', color: 'rgba(10, 10, 10, 0.85)',
          textAlign: 'left', cursor: 'default'},
          this.state.top!=null
            ? {top: this.state.top, maxHeight: 'calc(100vh - '+(this.state.top+12)+'px)'}
            : {bottom: this.state.bottom, maxHeight: 'calc(100vh - '+(this.state.bottom+12)+'px)'})}>
        <div style={{display: 'flex', alignItems: 'center', marginBottom: '6px'}}>
          <span style={{display: 'inline-block', width: '20px', height: '20px', lineHeight: '20px', borderRadius: '50%',
            backgroundColor: '#0F924E', color: 'white', fontSize: '11px', fontWeight: '600', textAlign: 'center',
            marginRight: '8px', flex: 'none'}}>{this.props.n}</span>
          <span style={{fontWeight: '600', fontSize: '14.5px', flex: 'auto'}}>{this.props.title}</span>
          <span onPointerDown={this.toggle.bind(this)} style={{cursor: 'pointer', color: '#999', fontSize: '18px',
            lineHeight: '18px', paddingLeft: '8px'}}>×</span>
        </div>
        {/* Talking points, like a slide; materialize hides list bullets unless the list is browser-default */}
        <ul className='browser-default' style={{margin: 0, paddingLeft: '18px'}}>
          {this.props.points.map((point, i)=><li key={i} style={{listStyleType: 'disc', marginBottom: '2px'}}>{point}</li>)}
        </ul>
        {this.props.example &&
          <div style={{marginTop: '10px', padding: '8px 10px', backgroundColor: '#F2FAF5', borderRadius: '6px',
            borderLeft: '3px solid #7AE1AC'}}>
            <div style={{fontSize: '11px', fontWeight: '600', color: '#0F924E', textTransform: 'uppercase',
              letterSpacing: '0.05em', marginBottom: '2px'}}>Example</div>
            {this.props.example}
          </div>}
        {this.props.note &&
          <div style={{marginTop: '10px', padding: '8px 10px', backgroundColor: '#F3F7FE', borderRadius: '6px',
            borderLeft: '3px solid #54A0F8'}}>
            <div style={{fontSize: '11px', fontWeight: '600', color: '#2F7BD9', textTransform: 'uppercase',
              letterSpacing: '0.05em', marginBottom: '2px'}}>Note: new in the revival</div>
            {this.props.note}
          </div>}
      </div>,
      document.body)
  }

  render(){
    if(markersOff){
      return null
    }
    var active = this.state.open || this.state.hover
    return (
      <span style={Object.assign({display: 'inline-block', verticalAlign: 'middle'}, this.props.style)}>
        <span ref={this.marker} title={this.props.title}
          onPointerDown={this.toggle.bind(this)} onPointerUp={this.stop} onPointerMove={this.stop}
          onMouseEnter={()=>this.setState({hover: true})} onMouseLeave={()=>this.setState({hover: false})}
          style={{display: 'inline-block', width: '18px', height: '18px', lineHeight: '16px', borderRadius: '50%',
            border: '1.5px solid '+(active ? '#0F924E' : '#b5b5b5'),
            backgroundColor: this.state.open ? '#0F924E' : 'white',
            color: this.state.open ? 'white' : (active ? '#0F924E' : '#9a9a9a'),
            opacity: active ? 1 : 0.7, fontFamily: 'Noto Sans', fontSize: '10.5px', fontWeight: '600',
            textAlign: 'center', cursor: 'pointer', userSelect: 'none', boxSizing: 'border-box',
            transition: 'opacity 0.15s, border-color 0.15s'}}>
          {this.props.n}
        </span>
        {this.state.open && this.renderCard()}
      </span>
    )
  }
}
