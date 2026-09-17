/** @odoo-module **/
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, useRef, useState, onMounted, onWillUpdateProps } from "@odoo/owl";

class SignaturePad extends Component {
    setup() {
        this.canvasRef = useRef("canvas");
        this.containerRef = useRef("container");
        this.state = useState({ value: this.props.record.data[this.props.name] || false });
        this.isDrawing = false;

        onMounted(() => {
            if (this.canvasRef.el) {
                this._setupCanvas();
            }
        });

        onWillUpdateProps((nextProps) => {
            this.state.value = nextProps.record.data[nextProps.name] || false;
        });
    }

    _setupCanvas() {
        const canvas = this.canvasRef.el;
        const container = this.containerRef.el;
        if (!canvas || !container) return;

        canvas.width = container.clientWidth;
        canvas.height = 200;

        const ctx = canvas.getContext("2d");
        ctx.lineCap = "round";
        ctx.lineJoin = "round";
        ctx.lineWidth = 2;
        ctx.strokeStyle = "#000";

        const getPos = (e) => {
            const rect = canvas.getBoundingClientRect();
            const clientX = e.clientX || (e.touches && e.touches[0].clientX);
            const clientY = e.clientY || (e.touches && e.touches[0].clientY);
            return { x: clientX - rect.left, y: clientY - rect.top };
        };

        const startDraw = (e) => {
            this.isDrawing = true;
            const pos = getPos(e);
            ctx.beginPath();
            ctx.moveTo(pos.x, pos.y);
        };

        const draw = (e) => {
            if (!this.isDrawing) return;
            const pos = getPos(e);
            ctx.lineTo(pos.x, pos.y);
            ctx.stroke();
        };

        const stopDraw = () => {
            if (!this.isDrawing) return;
            this.isDrawing = false;
            const dataUrl = canvas.toDataURL("image/png");
            const base64 = dataUrl.slice(dataUrl.indexOf(",") + 1).replace(/\s/g, "");
            if (!base64 || base64.length % 4 === 1) return;
            const normalizedBase64 = base64.padEnd(base64.length + (4 - base64.length % 4) % 4, "=");
            this.props.record.update({ [this.props.name]: normalizedBase64 });
            this.state.value = dataUrl;
        };

        this.getPreviewSrc = () => {
            if (!this.state.value) return false;
            return this.state.value.startsWith("data:")
                ? this.state.value
                : `data:image/png;base64,${this.state.value}`;
        };

        // Mouse
        canvas.addEventListener("mousedown", startDraw);
        canvas.addEventListener("mousemove", draw);
        canvas.addEventListener("mouseup", stopDraw);
        canvas.addEventListener("mouseleave", stopDraw);

        // Touch
        canvas.addEventListener("touchstart", (e) => { e.preventDefault(); startDraw(e); }, { passive: false });
        canvas.addEventListener("touchmove", (e) => { e.preventDefault(); draw(e); }, { passive: false });
        canvas.addEventListener("touchend", (e) => { e.preventDefault(); stopDraw(); });
    }

    onClear() {
        this.props.record.update({ [this.props.name]: false });
        this.state.value = false;
        if (this.canvasRef.el) {
            const ctx = this.canvasRef.el.getContext("2d");
            ctx.clearRect(0, 0, this.canvasRef.el.width, this.canvasRef.el.height);
        }
    }
}

SignaturePad.template = "cleangroup.SignaturePad";
SignaturePad.props = {
    ...standardFieldProps,
};

export const signaturePadField = {
    component: SignaturePad,
    supportedTypes: ["binary"],
};

registry.category("fields").add("signature_pad", signaturePadField);
