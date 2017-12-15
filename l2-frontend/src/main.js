import Vue from 'vue'
import JournalGetMaterialModal from './JournalGetMaterialModal.vue'
import DepartmentsForm from './DepartmentsForm.vue'
import store from './store'
import * as action_types from './store/action-types'

new Vue({
  el: '#app',
  store,
  components: {JournalGetMaterialModal, DepartmentsForm},
  data: {
    timeouts: {}
  },
  created() {
    let vm = this
    this.$store.watch((state) => (state.departments.all), () => {
      let diff = vm.$store.getters.diff_departments
      vm.$store.dispatch(action_types.UPDATE_DEPARTMENTS, 'update', diff).then((ok) => {
        if (Array.isArray(ok) && ok.length > 0) {
          for (let row of ok) {
            row.updated = true;
            console.log(0)
            ((r) => {
              console.log(1)
              if (timeouts.hasOwnProperty(r.pk) && timeouts[r.pk] !== null) {
                console.log(2)
                clearTimeout(timeouts[r.pk])
                timeouts[r.pk] = null
              }
              timeouts[r.pk] = setTimeout(() => {
                console.log(3)
                r.updated = false
                timeouts[r.pk] = null
              }, 2000)
            })(row)
          }
        }
      })
    }, {deep: true})
    this.$store.dispatch(action_types.GET_ALL_DEPARTMENTS).then()
  }
})
