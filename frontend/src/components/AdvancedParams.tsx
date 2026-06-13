import type { CloneLanguage } from "../api";

export interface AdvancedParamValues {
  numSteps: number;
  guidanceScale: number;
  language: CloneLanguage;
}

interface Props {
  value: AdvancedParamValues;
  onChange: (next: AdvancedParamValues) => void;
}

export default function AdvancedParams({ value, onChange }: Props) {
  return (
    <details className="advanced-params">
      <summary>高级参数</summary>
      <div className="advanced-params-row">
        <label>
          num_steps:
          <input
            type="number"
            min={1}
            max={100}
            value={value.numSteps}
            onChange={(e) =>
              onChange({ ...value, numSteps: Number(e.target.value) })
            }
          />
        </label>
        <label>
          guidance_scale:
          <input
            type="number"
            step={0.1}
            min={0}
            max={10}
            value={value.guidanceScale}
            onChange={(e) =>
              onChange({ ...value, guidanceScale: Number(e.target.value) })
            }
          />
        </label>
        <label>
          language:
          <select
            value={value.language}
            onChange={(e) =>
              onChange({ ...value, language: e.target.value as CloneLanguage })
            }
          >
            <option value="zh">zh</option>
            <option value="none">none</option>
          </select>
        </label>
      </div>
    </details>
  );
}
