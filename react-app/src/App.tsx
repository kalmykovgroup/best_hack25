import { useState } from 'react'
import { AddressSearchRedux } from './components/AddressSearchRedux'
import { logger } from './utils/logger'
import { AddressObject } from './types/api.types'
import { formatAddress } from './utils/formatAddress'
import './App.css'

function App() {
  const [selectedResult, setSelectedResult] = useState<AddressObject | null>(null)

  const handleSelectResult = (result: AddressObject) => {
    setSelectedResult(result)
    logger.log('Выбран адрес:', result)
    // Здесь можно добавить логику для отображения на карте
  }

  return (
    <div className="app">
      <div className="header">
        <h1>BEST HACK</h1>
        <div className="links">
          <a href="https://github.com/kalmykovgroup/best_hack25" target="_blank" rel="noopener noreferrer">
            GitHub
          </a>
          <a href="https://hh.ru/resume/811aeab6ff0eca91650039ed1f636b52357439" target="_blank" rel="noopener noreferrer">
            Резюме
          </a>
        </div>
      </div>

      <div className={`layout ${selectedResult ? 'has-selection' : ''}`}>
        <div className="left-panel">
          <AddressSearchRedux onSelectResult={handleSelectResult} />
        </div>

        <div className={`right-panel ${selectedResult ? 'visible' : ''}`}>
          <div className="selected-result">
            {selectedResult && (
              <>
                <h2>Выбранный адрес:</h2>
                <div className="result-details">
                  <p><strong>Нормализованный адрес:</strong> {formatAddress(selectedResult.locality, selectedResult.street, selectedResult.number)}</p>
                  {selectedResult.additionalInfo?.fullAddress && (
                    <p><strong>Полный адрес:</strong> {selectedResult.additionalInfo.fullAddress}</p>
                  )}
                  <p><strong>Координаты:</strong> {selectedResult.lat.toFixed(6)}, {selectedResult.lon.toFixed(6)}</p>
                  {selectedResult.additionalInfo?.postalCode && (
                    <p><strong>Индекс:</strong> {selectedResult.additionalInfo.postalCode}</p>
                  )}
                  {selectedResult.additionalInfo?.district && (
                    <p><strong>Район:</strong> {selectedResult.additionalInfo.district}</p>
                  )}
                  {selectedResult.score > 0 && (
                    <p><strong>Релевантность:</strong> {(selectedResult.score * 100).toFixed(0)}%</p>
                  )}
                  {selectedResult.additionalInfo?.tags && Object.keys(selectedResult.additionalInfo.tags).length > 0 && (
                    <div className="tags-section">
                      <p><strong>OSM теги:</strong></p>
                      <div className="tags-list">
                        {Object.entries(selectedResult.additionalInfo.tags).map(([key, value]) => (
                          <p key={key} className="tag-item">
                            <span className="tag-key">{key}:</span> {value}
                          </p>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
