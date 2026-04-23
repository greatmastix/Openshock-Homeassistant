class OpenShockShockerCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._config = null;
    this._hass = null;
    this._intensity = 50;
    this._duration = 1000;
  }

  setConfig(config) {
    if (!config || !config.device_id) {
      throw new Error('OpenShock Shocker card requires a device_id');
    }

    this._config = config;
    this._intensity = Number(config.intensity ?? 50);
    this._duration = Number(config.duration_ms ?? 1000);
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return 4;
  }

  _callCommand(command) {
    if (!this._hass || !this._config) {
      return;
    }

    const serviceData = {
      device_id: this._config.device_id,
      command,
    };

    if (command !== 'stop') {
      serviceData.intensity = this._intensity;
      serviceData.duration_ms = this._duration;
    }

    this._hass.callService('openshock', 'send_command', serviceData);
  }

  _onIntensityInput(value) {
    this._intensity = Number(value);
    const valueEl = this.shadowRoot?.getElementById('intensity-value');
    if (valueEl) {
      valueEl.textContent = String(this._intensity);
    }
  }

  _onDurationInput(value) {
    this._duration = Number(value);
    const valueEl = this.shadowRoot?.getElementById('duration-value');
    if (valueEl) {
      valueEl.textContent = String(this._duration);
    }
  }

  _render() {
    if (!this.shadowRoot || !this._config) {
      return;
    }

    const title = this._config.title ?? 'OpenShock Shocker';

    this.shadowRoot.innerHTML = `
      <style>
        ha-card {
          padding: 16px;
        }

        .title {
          font-size: 1.2rem;
          font-weight: 600;
          margin-bottom: 12px;
        }

        .field {
          margin-bottom: 12px;
        }

        .field-header {
          display: flex;
          justify-content: space-between;
          font-size: 0.95rem;
          margin-bottom: 4px;
        }

        .buttons {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 8px;
        }

        button {
          border: none;
          border-radius: 10px;
          padding: 10px;
          font-size: 0.95rem;
          cursor: pointer;
          background: var(--secondary-background-color);
          color: var(--primary-text-color);
        }

        button.primary {
          background: var(--primary-color);
          color: var(--text-primary-color);
        }

        button.danger {
          background: var(--error-color);
          color: var(--text-primary-color);
        }
      </style>
      <ha-card>
        <div class="title">${title}</div>

        <div class="field">
          <div class="field-header">
            <span>Intensity</span>
            <span id="intensity-value">${this._intensity}</span>
          </div>
          <input id="intensity" type="range" min="1" max="100" value="${this._intensity}" />
        </div>

        <div class="field">
          <div class="field-header">
            <span>Duration (ms)</span>
            <span id="duration-value">${this._duration}</span>
          </div>
          <input id="duration" type="range" min="100" max="30000" step="100" value="${this._duration}" />
        </div>

        <div class="buttons">
          <button class="primary" id="shock">Shock</button>
          <button id="vibrate">Vibrate</button>
          <button id="sound">Sound</button>
          <button class="danger" id="stop">Stop</button>
        </div>
      </ha-card>
    `;

    this.shadowRoot.getElementById('intensity')?.addEventListener('input', (event) => {
      this._onIntensityInput(event.target.value);
    });

    this.shadowRoot.getElementById('duration')?.addEventListener('input', (event) => {
      this._onDurationInput(event.target.value);
    });

    this.shadowRoot.getElementById('shock')?.addEventListener('click', () => this._callCommand('shock'));
    this.shadowRoot.getElementById('vibrate')?.addEventListener('click', () => this._callCommand('vibrate'));
    this.shadowRoot.getElementById('sound')?.addEventListener('click', () => this._callCommand('sound'));
    this.shadowRoot.getElementById('stop')?.addEventListener('click', () => this._callCommand('stop'));
  }
}

customElements.define('openshock-shocker-card', OpenShockShockerCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: 'openshock-shocker-card',
  name: 'OpenShock Shocker Card',
  description: 'Control an OpenShock device by Home Assistant device id.',
});
