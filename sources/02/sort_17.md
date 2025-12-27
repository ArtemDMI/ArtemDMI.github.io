В финальном уроке курса мы разберём, как оптимизировать Unity проект под Яндекс Игры, при этом рекомендуется использовать Unity 6, так как он лучше оптимизирован для WebGL платформы, чем старые версии, и имеет ряд новых инструментов, однако стоит учитывать, что шестая версия может немного увеличивать вес игры.

In the final lesson of the course, we will discuss how to optimize a Unity project for Yandex Games, and it is recommended to use Unity 6 as it is better optimized for the WebGL platform than older versions and has a number of new tools, but it is worth considering that the sixth version may slightly increase the game's weight.

---

При импорте плагина автоматически применяются оптимальные настройки проекта для Яндекс Игр, но всё же есть опции, которые требуют внимания, например, включение кеширования позволяет игре быстрее загружаться при повторных запусках, но на устройствах iOS могут возникнуть проблемы, и в таком случае рекомендуется отключить кеширование.

When importing the plugin, optimal project settings for Yandex Games are automatically applied, but there are still options that require attention, for example, enabling caching allows the game to load faster on subsequent launches, but problems may arise on iOS devices, in which case it is recommended to disable caching.

---

Для WebGL рекомендуется использовать настройку Gamma вместо Linear, так как она поддерживается на большем количестве устройств и улучшает производительность, к тому же по умолчанию сначала инициализируется SDK, а затем загружается игра.

For WebGL, it is recommended to use the Gamma setting instead of Linear, as it is supported on more devices and improves performance; additionally, by default, the SDK is initialized first, and then the game is loaded.

---

Если включить опцию Async Init SDK, игра и SDK будут загружаться одновременно, что поможет ускорить загрузку, однако это требует тестирования, так как возможны ошибки, если SDK не успевает инициализироваться.

If you enable the Async Init SDK option, the game and the SDK will load simultaneously, which will help speed up loading, however, this requires testing as errors are possible if the SDK does not have time to initialize.

---

Опция снижения разрешения на мобильных устройствах позволяет улучшить производительность, поэтому настройте коэффициент качества в пределах 1.3–2 в зависимости от баланса между качеством и производительностью, и рекомендуется установить минимальное сжатие для managed кода, чтобы избежать проблем с нестабильностью.

The option to reduce resolution on mobile devices allows for improved performance, so adjust the quality factor within the range of 1.3–2 depending on the balance between quality and performance, and it is recommended to set minimal compression for managed code to avoid stability issues.

---

Отключите логотип Unity, чтобы ускорить загрузку игры, и если используете картинку для фона, учтите, что она увеличивает вес, а удаление лишних пакетов в Unity может немного снизить вес билда, но для корректной работы плагина WebGL надо оставить определённые пакеты.

Disable the Unity logo to speed up the game's loading, and if you use a background image, keep in mind that it increases the weight, while removing unnecessary packages in Unity can slightly reduce the build's weight, but for the WebGL plugin to work correctly, you need to keep certain packages.

---

Зависимости в Unity начинаются со сцен, которые содержат объекты с компонентами в скриптах, которые, в свою очередь, могут иметь дополнительные ссылки на другие объекты или ресурсы, и важно контролировать эти зависимости, чтобы избежать ненужных ресурсов, улучшить производительность и снизить вес игры.

Dependencies in Unity start with scenes that contain objects with components in scripts, which in turn can have additional links to other objects or resources, and it is important to control these dependencies to avoid unnecessary resources, improve performance, and reduce the game's weight.

---

Сцены и префабы тоже имеют вес, и это надо учитывать, поэтому если есть возможность процедурно генерировать уровни, это может стать хорошей экономией веса игры, а в Edit Log можно просматривать ресурсы, которые попали в билд игры, что полезно для выявления ненужных или дублирующих ассетов.

Scenes and prefabs also have weight, and this must be taken into account, so if it is possible to procedurally generate levels, this can be a good way to save game weight, and in the Edit Log, you can view the resources that made it into the game build, which is useful for identifying unnecessary or duplicate assets.

---

Используйте опцию Use Crunch Compression для уменьшения веса текстур, а для текстур на объектах, которые вытягиваются вдаль, например, земля или стена, включите Generate Mip Maps, чтобы были сгенерированы несколько текстур разного разрешения, а в ином случае отключайте эту опцию для экономии веса.

Use the Use Crunch Compression option to reduce the weight of textures, and for textures on objects that stretch into the distance, such as the ground or a wall, enable Generate Mip Maps to generate several textures of different resolutions; otherwise, disable this option to save weight.

---

Можно использовать белые текстуры для элементов интерфейса и изменять их цвет, чтобы избежать дублирования текстур для разных цветов, а для UI-панелей полезно использовать Sprite Editor, чтобы панели могли масштабироваться без искажений вместо создания текстур большого размера.

You can use white textures for interface elements and change their color to avoid duplicating textures for different colors, and for UI panels, it is useful to use the Sprite Editor so that the panels can be scaled without distortion instead of creating large-sized textures.

---

Для градиентов можно использовать узкие текстуры, например, один пиксель на 256 пикселей, что уменьшает вес игры и сохраняет визуальное качество, а текстура неба, которая зачастую имеет большой вес, может быть заменена на шейдер или на легковесный градиент.

For gradients, you can use narrow textures, for example, one pixel by 256 pixels, which reduces the game's weight and preserves visual quality, and the sky texture, which often has a large weight, can be replaced with a shader or a lightweight gradient.

---

Не используйте стандартный шрифт, который по умолчанию есть в Unity, так как он не отображается в WebGL, и при выборе шрифтов смотрите на их вес, поскольку они бывают очень тяжёлые, а если не использовать TextMeshPro, можно сэкономить немного веса.

Do not use the default font that comes with Unity, as it does not display in WebGL, and when choosing fonts, look at their weight, as they can be very heavy; you can also save some weight by not using TextMeshPro.

---

Ещё сэкономить вес можно с помощью сжатия анимаций, например, для сжатия анимации персонажа используйте опцию Keyframe Reduction, и можно ещё настроить коэффициент, но смотрите, чтобы анимация не потеряла в качестве.

You can also save weight by compressing animations; for example, to compress a character's animation, use the Keyframe Reduction option, and you can also adjust the factor, but make sure the animation does not lose quality.

---

Установите параметр Decompression on Load для всех звуков, чтобы избежать ошибок на WebGL, и используйте формат PCM для коротких звуков и Vorbis со сжатием на 50% для музыки, а длинные аудиофайлы можно сократить и зациклить.

Set the Decompression on Load parameter for all sounds to avoid errors on WebGL, and use the PCM format for short sounds and Vorbis with 50% compression for music, while long audio files can be shortened and looped.

---

Если в игре слышны посторонние звуки или трески, попробуйте переключить параметр в настройках звука, а также уменьшите количество батчей, на которые влияет количество материалов, текстур, шейдеров и полигонов в вашей игре.

If you hear extraneous sounds or crackling in the game, try switching the parameter in the sound settings, and also reduce the number of batches, which is affected by the number of materials, textures, shaders, and polygons in your game.

---

Вы можете сократить количество отрисовок одинаковых объектов, включив опцию Dynamic Batching и GPU Instancing для соответствующих материалов, при этом Static Batching может улучшить оптимизацию, но не всегда даёт значительный прирост, зато прибавляет вес игре.

You can reduce the number of draw calls for identical objects by enabling the Dynamic Batching and GPU Instancing options for the corresponding materials, while Static Batching can improve optimization but does not always provide a significant boost and adds weight to the game.

---

Опция Static Batching объединяет несколько сеток в одну, для этого необходимо пометить объекты, которые не будут двигаться в кадре, как статичные, и вы можете запечь Occlusion Culling, чтобы исключить из отрисовки объекты, скрытые другими объектами.

The Static Batching option combines several meshes into one; to do this, you need to mark objects that will not move in the frame as static, and you can bake Occlusion Culling to exclude objects hidden by other objects from rendering.

---

Контролируйте количество объектов на сцене, чтобы не перегружать оперативную память, и если есть много объектов, которые можно показывать в разное время, загружайте такие ресурсы только тогда, когда они требуются, и выгружайте, если они уже не используются.

Control the number of objects on the scene to avoid overloading RAM, and if there are many objects that can be shown at different times, load such resources only when they are needed and unload them if they are no longer in use.

---

Это можно сделать с помощью простого создания и удаления префаба или можно загружать ресурсы, которые находятся в папке "Resources", но имейте в виду, что файлы, находящиеся в папках "Resources" и "StreamingAssets", в любом случае попадут в билд.

This can be done by simply creating and deleting a prefab, or you can load resources located in the "Resources" folder, but keep in mind that files in the "Resources" and "StreamingAssets" folders will be included in the build anyway.

---

Иногда сторонние ассеты содержат что-то лишнее в этих папках, так что проверяйте их, и очень полезным может стать инструмент Addressables, который позволяет упаковывать ресурсы в отдельные пакеты и во время выполнения игры загружать их.

Sometimes third-party assets contain something extra in these folders, so check them, and the Addressables tool can be very useful, as it allows you to package resources into separate bundles and load them during the game's runtime.

---

Это может быть, например, целый уровень с моделями, текстурами и сценами, и такой подход позволяет сильно снизить вес игры за счёт того, что пакеты не будут помещены в основной билд игры, а будут загружены по мере необходимости, причём хранить их можно даже на отдельном сервере.

This could be, for example, an entire level with models, textures, and scenes, and this approach can significantly reduce the game's weight because the bundles will not be included in the main game build but will be loaded as needed, and they can even be stored on a separate server.

---

Эти рекомендации помогут оптимизировать Unity-проект для Яндекс Игр, улучшить производительность и сократить вес игры, и если вы посмотрели весь курс и ознакомились с документацией, вы точно готовы к публикации собственных проектов на платформе.

These recommendations will help optimize a Unity project for Yandex Games, improve performance, and reduce the game's weight, and if you have watched the entire course and reviewed the documentation, you are definitely ready to publish your own projects on the platform.

---

На этом мы завершаем курс по плагину Yandex Games, присоединяйтесь к нашему Telegram-каналу, где вы сможете задать вопросы и найти ответы, а также пообщаться с другими разработчиками.

This concludes our course on the Yandex Games plugin; join our Telegram channel where you can ask questions and find answers, as well as communicate with other developers.

---

Спасибо, что смотрели курс, и удачных вам релизов!

Thank you for watching the course, and we wish you successful releases!
