import { Component } from 'react';

// A render error anywhere below would otherwise leave a blank white page. This shows the error instead and
// lets you carry on: "Try again" re-renders, "Reload" restarts the page (your circuit is not lost by Try again).
export class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error('UI error:', error, info?.componentStack);
  }

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;
    return (
      <div style={{ padding: 24, font: '14px system-ui, sans-serif', maxWidth: 720 }}>
        <h2>Something went wrong in the editor</h2>
        <pre style={{ whiteSpace: 'pre-wrap', background: '#fde7e5', color: '#7a1a14', padding: 12, borderRadius: 4 }}>
          {String(error?.message ?? error)}
        </pre>
        <p>Copy the text above and send it so it can be fixed. The circuit in memory is untouched by "Try again".</p>
        <button type="button" onClick={() => this.setState({ error: null })}>Try again</button>{' '}
        <button type="button" onClick={() => window.location.reload()}>Reload</button>
      </div>
    );
  }
}
