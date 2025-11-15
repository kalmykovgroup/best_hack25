import { useState } from 'react'
import { AddressSearchRedux } from './components/AddressSearchRedux'
import { logger } from './utils/logger'
import { AddressObject } from './types/api.types'
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
      <h1>BEST HACK</h1>

      <AddressSearchRedux onSelectResult={handleSelectResult} />

      {selectedResult && (
        <div className="selected-result">
          <h2>Выбранный адрес:</h2>
          <div className="result-details">
            <p><strong>Адрес:</strong> {selectedResult.locality}, {selectedResult.street} {selectedResult.number}</p>
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
          </div>
        </div>
      )}
    </div>
  )
}

export default App
